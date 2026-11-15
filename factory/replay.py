#!/usr/bin/env python3
"""Replay one piece of evidence on BASE and BRANCH, side by side.

  replay.py E3                       # replay with the archived scenario
  replay.py E3 --scenario my.cs      # replay with an edited scenario (owner exploring)
  replay.py E3 --json                # machine output for the passport page

Runs in two isolated git worktrees (paths in sandbox.yaml). Nothing is committed or pushed.
"""
import argparse, concurrent.futures as cf, datetime, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
import yaml

HERE = Path(__file__).parent
REPEAT = 3


def load(req="REQ-2297"):
    repro = yaml.safe_load((HERE / f"repro-{req}.yaml").read_text())
    sb = yaml.safe_load((HERE / "sandbox.yaml").read_text())
    return repro, sb


def env(sb):
    e = dict(os.environ)
    e.update({"DOTNET_ROOT": sb["dotnet_root"], "PATH": sb["dotnet_root"] + os.pathsep + e["PATH"],
              "NUGET_PACKAGES": sb["nuget_packages"], "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"})
    return e


def git(wt, *a):
    return subprocess.run(["git", "-C", str(wt), *a], capture_output=True, text=True)


KEEP = re.compile(r"error CS\d+|Assert\.|Failure|excluded|^\s+(Passed|Failed) [A-Z]|Total tests")


def summarize(out):
    lines = [l.rstrip() for l in out.splitlines() if KEEP.search(l) and "warning" not in l]
    seen, uniq = set(), []
    for l in lines:
        k = re.sub(r"\[\d+(\.\d+)? ?m?s\]|\[xUnit\.net [^\]]+\]", "", l).strip()
        if k and k not in seen:
            seen.add(k); uniq.append(k[:220])
    return uniq[:18]


def run_dotnet_test(spec, wt, scenario_text, e):
    dest = Path(wt) / spec["scenario"]["dest"]
    tracked = git(wt, "ls-files", "--error-unmatch", spec["scenario"]["dest"]).returncode == 0
    dest.write_text(scenario_text, encoding="utf-8")
    try:
        t0 = time.time()
        statuses, out = [], ""
        for i in range(REPEAT):  # anti-flaky guard
            cmd = ["dotnet", "test", "tests/MessagePack.SourceGenerator.Tests", "-c", "Release",
                   "--filter", spec["filter"], "--logger", "console;verbosity=detailed"] + ([] if i == 0 else ["--no-build"])
            p = subprocess.run(cmd, cwd=wt, capture_output=True, text=True, env=e)
            o = p.stdout + p.stderr
            out = out or o
            f_ = re.findall(r"^\s+Failed [A-Z]\w*\.", o, re.M); p_ = re.findall(r"^\s+Passed [A-Z]\w*\.", o, re.M)
            statuses.append("fails" if f_ else "passes" if p_ else "build")
            if statuses[-1] == "build":
                break
        if statuses[0] == "build":
            status = "build error" if re.search(r"error CS\d+", out) else "unknown"
        elif len(set(statuses)) > 1:
            status = "unstable"
        else:
            status = statuses[0]
        return {"status": status, "runs": statuses, "lines": summarize(out), "seconds": round(time.time() - t0)}
    finally:
        if tracked:
            git(wt, "checkout", "--", spec["scenario"]["dest"])
        else:
            dest.unlink(missing_ok=True)


def run_e2e(spec, wt, scenario_text, e, side, sb):
    root = Path(sb["e2e_workdir"]) / side
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    shutil.copy(HERE / "e2e/Consumer/Consumer.csproj", root / "Consumer.csproj")
    (root / "Model.cs").write_text(scenario_text, encoding="utf-8")
    t0 = time.time()
    b = subprocess.run(["dotnet", "build", "-c", "Release", f"-p:MessagePackRepo={wt}"], cwd=root,
                       capture_output=True, text=True, env=e)
    if b.returncode != 0:
        return {"status": "build error", "lines": summarize(b.stdout + b.stderr), "seconds": round(time.time() - t0)}
    r = subprocess.run(["dotnet", sb["e2e_runner_dll"], str(root / "bin/Release")], capture_output=True, text=True, env=e)
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    return {"status": "ran", "lines": lines[:30], "seconds": round(time.time() - t0)}


def run_e2e_project(spec, wt, scenario_text, e, side, sb, req):
    """Copy a multi-project template, build it against this side's generator, run it.
    Repeated REPEAT times (anti-flaky guard): run 1 builds everything, later runs rebuild only the consumer
    project (--no-dependencies) so the analyzer/generator execute again on the same inputs."""
    root = Path(sb["e2e_workdir"]) / f"{req}-{side}"
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(HERE / spec["template"], root)
    (root / spec["scenario"]["dest"]).write_text(scenario_text, encoding="utf-8")
    t0 = time.time()
    outcomes = []
    for i in range(REPEAT):
        cmd = ["dotnet", "build", spec["build"], "-c", "Release", f"-p:MessagePackRepo={wt}", "--no-incremental"]
        b = subprocess.run(cmd + ([] if i == 0 else ["--no-dependencies"]), cwd=root, capture_output=True, text=True, env=e)
        out = b.stdout + b.stderr
        warns = sorted({re.sub(r"\s*\[[^\]]*\]$", "", m.group(0)).strip()[:200] for m in re.finditer(spec["warn_regex"] + r"[^\n]*", out)})
        lines = ["warnings: " + (str(len(warns)) if warns else "none")] + ["  " + w for w in warns]
        if b.returncode != 0:
            outcomes.append(("build error", lines + summarize(out)))
            break
        r = subprocess.run(["dotnet", "run", "--no-build", "-c", "Release", "--project", spec["run"]], cwd=root,
                           capture_output=True, text=True, env=e)
        lines += [l for l in r.stdout.splitlines() if l.strip()][:20]
        outcomes.append(("ran" + (" with warnings" if warns else ""), lines))
    status, lines = outcomes[0]
    if len(set((s, tuple(l)) for s, l in outcomes)) > 1:
        status = "unstable"
    return {"status": status, "runs": [s for s, _ in outcomes], "lines": lines, "seconds": round(time.time() - t0)}


def replay(eid, scenario_override=None, req="REQ-2297"):
    repro, sb = load(req)
    spec = repro["evidence"][eid]
    original = (HERE / spec["scenario"]["file"]).read_text(encoding="utf-8")
    text = Path(scenario_override).read_text(encoding="utf-8") if scenario_override else original
    e = env(sb)
    git(sb["worktree_head"], "checkout", "-q", "-f", repro["head"])
    git(sb["worktree_base"], "checkout", "-q", "-f", repro["base"])
    sides = {"base": sb["worktree_base"], "branch": sb["worktree_head"]}

    def go(side):
        wt = sides[side]
        if spec["kind"] == "dotnet-test":
            return side, run_dotnet_test(spec, wt, text, e)
        if spec["kind"] == "e2e-project":
            return side, run_e2e_project(spec, wt, text, e, side, sb, req)
        return side, run_e2e(spec, wt, text, e, side, sb)

    with cf.ThreadPoolExecutor(2) as ex:
        res = dict(ex.map(go, ["base", "branch"]))
    if "unstable" in (res["base"]["status"], res["branch"]["status"]):
        verdict = "unstable result — not valid as evidence"
    else:
        verdict = None
    differs = (res["base"]["status"] != res["branch"]["status"]) or (
        spec["kind"] in ("e2e-consumer", "e2e-project") and res["base"]["lines"] != res["branch"]["lines"])
    return {"evidence": eid, "title": spec["title"], "kind": spec["kind"],
            "scenario_file": spec["scenario"]["file"], "scenario_modified": text != original,
            "base_ref": repro["base"], "head_ref": repro["head"],
            "base": res["base"], "branch": res["branch"],
            "verdict": verdict or ("different behaviour" if differs else "identical behaviour"),
            "repeat": REPEAT if spec["kind"] in ("dotnet-test", "e2e-project") else 1,
            "replayed_at": datetime.datetime.now().isoformat(timespec="seconds")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("evidence"); ap.add_argument("--scenario"); ap.add_argument("--json", action="store_true")
    ap.add_argument("--req", default="REQ-2297")
    a = ap.parse_args()
    r = replay(a.evidence, a.scenario, a.req)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2)); return
    print(f"{r['evidence']} — {r['title']}\n  {r['verdict'].upper()}  (scenario modified: {r['scenario_modified']})")
    for side in ("base", "branch"):
        s = r[side]
        print(f"\n  [{side}] {s['status']} ({s['seconds']} s){'  runs: ' + '/'.join(s['runs']) if s.get('runs') else ''}")
        for l in s["lines"]:
            print("     " + l)


if __name__ == "__main__":
    main()
