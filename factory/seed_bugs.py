#!/usr/bin/env python3
"""Seeded-bug benchmark for the deterministic layer of the factory.

Each seed applies a typical agent defect on top of ju26-issue-2297 in a scratch worktree
(LOCAL branches only, never pushed), rebuilds the passport, and records whether the
factory FLAGGED it (a rule names it), only ROUTED it to the owner's reading contract,
or MISSED it. Executed evidence (dotnet tests) is not re-run here: this measures the
deterministic layer alone.

Usage: seed_bugs.py --worktree WT --out out/
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).parent))
import passport
import replay

HERE = Path(__file__).parent


def sh(wt, *a):
    return subprocess.run(["git", "-C", str(wt), *a], capture_output=True, text=True, check=True).stdout


def edit(wt, path, fn):
    p = Path(wt) / path
    raw = p.read_bytes() if p.exists() else b""
    bom = raw.startswith(b"\xef\xbb\xbf")
    t = raw.decode("utf-8-sig")
    n = fn(t)
    assert n != t, f"seed did not change {path}"
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + n.encode("utf-8"))  # keep the BOM: only the seeded defect may differ


def first_snapshot_with(wt, needle):
    out = subprocess.run(["git", "-C", str(wt), "grep", "-l", needle, "--", "tests/*Resources*/*.g.cs"],
                         capture_output=True, text=True).stdout.split("\n")
    return next(p for p in out if p)


def seeds(wt):
    snap = first_snapshot_with(wt, "writer.WriteArrayHeader(1);")
    enum_snaps = [p for p in sh(wt, "ls-files", "tests/MessagePack.SourceGenerator.Tests/Resources").split("\n") if "EnumFormatter" in p and p.endswith(".g.cs") and "MyEnumFormatter" in p]
    return [
        dict(id="S1", what="Behaviour change hidden in a regenerated snapshot", files=[snap],
             apply=lambda: edit(wt, snap, lambda t: t.replace("writer.WriteArrayHeader(1);", "writer.WriteArrayHeader(2);", 1))),
        dict(id="S2", what="The agent “forgets” a template (Enum) and regenerates the snapshots to match",
             files=["src/MessagePack.SourceGenerator/Transforms/EnumTemplate.tt"] + enum_snaps,
             apply=lambda: [edit(wt, p, lambda t: re.sub(r"#if !NETSTANDARD2_0 && !NETFRAMEWORK\r?\n\t?\[global::System\.Diagnostics\.CodeAnalysis\.ExcludeFromCodeCoverage\]\r?\n#endif\r?\n", "", t))
                            for p in ["src/MessagePack.SourceGenerator/Transforms/EnumTemplate.tt"] + enum_snaps]),
        dict(id="S3", what="Unrequested change in the runtime", files=["src/MessagePack/MessagePackWriter.cs"],
             apply=lambda: edit(wt, "src/MessagePack/MessagePackWriter.cs", lambda t: t.replace("public void WriteNil()", "public void WriteNil() // tweak", 1))),
        dict(id="S4", what="Assertion removed from an existing test", files=["tests/MessagePack.SourceGenerator.Tests/GenerationTests.cs"],
             apply=lambda: edit(wt, "tests/MessagePack.SourceGenerator.Tests/GenerationTests.cs",
                                lambda t: re.sub(r"\n[^\n]*\[Fact\][^\n]*\n", "\n", t, count=1))),
        dict(id="S5", what="Silent addition to the public API", files=["src/MessagePack/net8.0/PublicAPI.Unshipped.txt"],
             apply=lambda: edit(wt, "src/MessagePack/net8.0/PublicAPI.Unshipped.txt", lambda t: t + "MessagePack.MessagePackSerializer.Debug() -> void\n")),
        dict(id="S6", what="Build change (props) slipped into the change", files=["Directory.Build.props"],
             apply=lambda: edit(wt, "Directory.Build.props", lambda t: t.replace("</Project>", "  <PropertyGroup><TreatWarningsAsErrors>false</TreatWarningsAsErrors></PropertyGroup>\n</Project>", 1))),
        dict(id="S7", what="Logic change in a template (.tt) unrelated to the requirement", files=["src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt"],
             apply=lambda: edit(wt, "src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt", lambda t: t.replace("writer.WriteNil();", "writer.WriteNil(); writer.WriteNil();", 1))),
        dict(id="S8", what="The agent weakens its own new test", files=["tests/MessagePack.SourceGenerator.Tests/CodeCoverageExclusionTests.cs"],
             apply=lambda: edit(wt, "tests/MessagePack.SourceGenerator.Tests/CodeCoverageExclusionTests.cs", lambda t: t.replace("generated.Count >= 5", "generated.Count >= 0", 1))),
        dict(id="S9", what="CONTROL: method merely moved within the runtime (not a bug)", files=["src/MessagePack/MessagePackWriter.cs"],
             control=True, apply=lambda: edit(wt, "src/MessagePack/MessagePackWriter.cs", move_method)),
    ]


def move_method(t):
    """Cut the WriteNil() method and paste it just before the last closing brace of the file."""
    i = t.index("public void WriteNil()")
    start = t.rfind("\n", 0, t.rfind("///", 0, i)) + 1 if "///" in t[max(0, i - 400):i] else t.rfind("\n", 0, i) + 1
    j = t.index("{", i); depth = 0
    for k in range(j, len(t)):
        depth += t[k] == "{"; depth -= t[k] == "}"
        if depth == 0:
            end = t.index("\n", k) + 1; break
    block = t[start:end]
    rest = t[:start] + t[end:]
    last = rest.rstrip().rfind("}")
    last = rest.rfind("}", 0, last)
    return rest[:last] + block + rest[last:]


def classify(p, files):
    flagged_files = {m["file"] for m in p["mechanical"]["flagged"]} | {o["file"] for o in p["traceability"]["orphans"]} \
        | {w["file"] for w in p["weakened_tests"]} \
        | {t["source"] for t in p.get("tests", []) if t.get("origin") == "agent" and "tautology" in t.get("issues", [])}
    text = json.dumps(p["verdict"], ensure_ascii=False)
    cov = next((e for e in p["evidence"] if e["id"] == "REGEN" and e["result"] == "fail"), None)
    zones_major = [z["zone"] for z in p["zones"] if z.get("severity") == "major"]
    if any(f in flagged_files for f in files) or cov or zones_major:
        how = []
        if any(f in flagged_files for f in files): how.append("mechanical rule / orphan / weakened or tautological test")
        if cov: how.append("test suite failing (regeneration + tests)")
        if zones_major: how.append("major zone → RED")
        return "flagged", ", ".join(how)
    must = {m["file"] for m in p["reading_contract"]["must_read"]}
    if any(f in must for f in files):
        return "routed to human reading", "in the reading contract, with no rule naming it"
    return "missed", "neither flagged nor in the reading contract"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--worktree", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(); wt = a.worktree
    results = []
    for s in seeds(wt):
        sh(wt, "checkout", "-q", "-f", "origin/ju26-issue-2297")
        sh(wt, "checkout", "-q", "-B", f"local-seed-{s['id']}")
        s["apply"]()
        sh(wt, "-c", "user.name=seed", "-c", "user.email=seed@localhost", "commit", "-qam", f"seed {s['id']}")
        # Real regeneration evidence: run the snapshot test suite on this seeded branch (generic rule:
        # generated files are proven only if regenerating them reproduces the committed version).
        repro, sb = replay.load("REQ-2297")
        t = subprocess.run(["dotnet", "test", "tests/MessagePack.SourceGenerator.Tests", "-c", "Release"],
                           cwd=wt, capture_output=True, text=True, env=replay.env(sb))
        ok = bool(re.search(r"Passed!\s+-\s+Failed:\s+0", t.stdout))
        ev = Path(a.out) / f".seed-{s['id']}-evidence.json"
        ev.write_text(json.dumps({"runs": [{"id": "REGEN", "type": "executed", "by": "test suite (regenerates the snapshots)",
                                            "what": "regeneration", "result": "pass" if ok else "fail", "regenerates": ["snapshots"]}]}))
        args = SimpleNamespace(repo=wt, req=str(HERE / "requirements/REQ-2297.yaml"), evidence=str(ev), ai=None, verif=None,
                               head="HEAD", out=a.out, tests=None, catching=None)
        p = passport.build(args)
        if s.get("control"):
            excl = [x for x in p["reading_contract"]["excluded"] if "moved" in x["what"]]
            in_read = [m for m in p["reading_contract"]["must_read"] if m["file"] in s["files"]]
            status = "control OK: excluded as a move" if excl and not in_read else "control KO: read or flagged"
            how = (excl[0]["proof"][:120] if excl else f"{len(in_read)} hunk(s) in the reading contract")
        else:
            status, how = classify(p, s["files"])
        results.append({"id": s["id"], "what": s["what"], "status": status, "how": how, "lane": p["verdict"]["lane"],
                        "lines_to_read": p["reading_contract"]["lines_to_read"]})
        print(f"{s['id']}: {status:28} lane {p['verdict']['lane']:6} — {s['what']} [{how}]")
    sh(wt, "checkout", "-q", "-f", "origin/ju26-issue-2297")
    bugs = [r for r in results if not r["id"] == "S9"]
    n = len(bugs); fl = sum(r["status"] == "flagged" for r in bugs); ro = sum(r["status"].startswith("routed") for r in bugs)
    summary = {"seeds": n, "flagged": fl, "routed_to_reading": ro, "missed": n - fl - ro, "results": results}
    Path(a.out, "seeded-bugs-2297.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nFlagged {fl}/{n} · routed to human reading {ro}/{n} · missed {n-fl-ro}/{n}")


if __name__ == "__main__":
    main()
