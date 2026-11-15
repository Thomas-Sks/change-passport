#!/usr/bin/env python3
"""Diff-scoped mutation testing ("revert one hunk") for an agent change.

Operator: for every changed hunk in compiled source (*.cs under src/, excluding generated
snapshots and T4 sources), revert ONLY that hunk on top of the branch, then run two test sets:
  - the tests delivered by the agent with the change
  - the full test project
A mutant that survives = a change that no test notices. Survivors push the passport to ORANGE.

Usage: mutate.py --req requirements/REQ-2297.yaml --agent-filter FullyQualifiedName~CodeCoverageExclusionTests --out out
Runs in the branch worktree (sandbox.yaml). LOCAL only; the worktree is reset after each mutant.
"""
import argparse, json, re, subprocess, time
from pathlib import Path
import yaml
import replay  # env + sandbox config

HERE = Path(__file__).parent


def git(wt, *a, inp=None):
    # bytes in/out: keep CRLF intact so single-hunk patches still apply
    r = subprocess.run(["git", "-C", str(wt), "-c", "core.quotepath=off", *a], capture_output=True,
                       input=inp.encode("utf-8") if inp is not None else None)
    r.stdout, r.stderr = r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")
    return r


def hunks(wt, base, head):
    files = [f for f in git(wt, "diff", "--name-only", base, head).stdout.split("\n")
             if f.startswith("src/") and f.endswith(".cs")]
    out = []
    for f in files:
        d = git(wt, "diff", "-U0", "--no-color", base, head, "--", f).stdout
        header, body = d.split("\n@@", 1)[0], "@@" + d.split("\n@@", 1)[1]
        parts = re.split(r"(?m)^(?=@@ )", body)  # (?m) ^ also matches after \r\n
        for i, h in enumerate(p for p in parts if p.strip()):
            out.append({"file": f, "index": i + 1, "header": h.split("\n", 1)[0],
                        "patch": header + "\n" + h if h.endswith("\n") else header + "\n" + h + "\n"})
    return out


def run_tests(wt, flt, e):
    cmd = ["dotnet", "test", "tests/MessagePack.SourceGenerator.Tests", "-c", "Release"]
    if flt:
        cmd += ["--filter", flt]
    p = subprocess.run(cmd, cwd=wt, capture_output=True, text=True, env=e)
    out = p.stdout + p.stderr
    m = re.search(r"Failed:\s+(\d+),\s+Passed:\s+(\d+)", out)
    if m:
        return "killed" if int(m.group(1)) > 0 else "survived", f"{m.group(1)} failed / {m.group(2)} passed"
    return ("killed" if re.search(r"error CS\d+", out) else "unknown"), "build failed" if "error CS" in out else "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--req", required=True); ap.add_argument("--agent-filter", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    req = yaml.safe_load(Path(a.req).read_text())
    repro, sb = replay.load(req['id']); e = replay.env(sb); wt = sb["worktree_head"]
    head = repro["head"]
    git(wt, "checkout", "-q", "-f", head)
    muts = hunks(wt, req["base"], head)
    results = []
    for i, m in enumerate(muts, 1):
        git(wt, "checkout", "-q", "-f", head)
        ap_ = git(wt, "apply", "-R", "--unidiff-zero", "-", inp=m["patch"])
        if ap_.returncode != 0:
            results.append({**{k: m[k] for k in ("file", "index", "header")}, "id": f"M{i}", "error": ap_.stderr.strip()[:200]}); continue
        t0 = time.time()
        agent = run_tests(wt, a.agent_filter, e)
        full = run_tests(wt, None, e)
        r = {"id": f"M{i}", "file": m["file"], "index": m["index"], "header": m["header"],
             "agent_tests": agent[0], "agent_detail": agent[1], "full_suite": full[0], "full_detail": full[1],
             "seconds": round(time.time() - t0)}
        results.append(r)
        print(f"{r['id']} {m['file'].split('/')[-1]} {m['header'][:40]:40}  agent: {agent[0]:7} suite: {full[0]:7} ({r['seconds']} s)", flush=True)
    git(wt, "checkout", "-q", "-f", head)
    ok = [r for r in results if "error" not in r]
    summary = {"operator": "revert-one-hunk", "mutants": len(ok),
               "killed_by_agent_tests": sum(r["agent_tests"] == "killed" for r in ok),
               "killed_by_full_suite": sum(r["full_suite"] == "killed" for r in ok),
               "survivors_full_suite": [r["id"] for r in ok if r["full_suite"] != "killed"],
               "results": results}
    Path(a.out, f"mutation-{req['id']}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nAgent tests: {summary['killed_by_agent_tests']}/{len(ok)} mutants killed · full suite: {summary['killed_by_full_suite']}/{len(ok)}")


if __name__ == "__main__":
    main()
