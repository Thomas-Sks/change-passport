#!/usr/bin/env python3
"""Just-in-time "catching" tests (inspired by Meta JiTTests, FSE 2026).

1. A generator model (different from the authoring agent) reads the LOCKED acceptance criteria
   and the non-mechanical diff, and writes disposable test scenarios that assert the criteria.
2. Every scenario runs on BASE and on BRANCH in the sandbox worktrees.
3. Classification per scenario:
     base passes, branch fails -> CATCH: behaviour changed against a criterion (regression or decision)
     base fails,  branch passes -> IMPLEMENTATION PROVEN (fail-before / pass-after)
     same on both              -> no information, discarded
4. Catches become passport evidence, each replayable with one click (repro.yaml).
The scenarios are never committed to the repository.

Usage: catching.py --req requirements/REQ-2297.yaml --out out [--model sonnet] [--reuse]
"""
import argparse, concurrent.futures as cf, json, re, subprocess, time
from pathlib import Path
import yaml
import replay

HERE = Path(__file__).parent
DEST = "tests/MessagePack.SourceGenerator.Tests/CatchingTests.cs"

HARNESS = '''// Harness available (copy it as-is into your class):
private static async Task<(Compilation Output, ImmutableArray<Diagnostic> Diags)> RunAsync(string source)
{
    ImmutableArray<MetadataReference> refs = await ReferencesHelper.DefaultTargetFrameworkReferences.ResolveAsync(LanguageNames.CSharp, CancellationToken.None);
    CSharpCompilation compilation = CSharpCompilation.Create("Catching",
        [CSharpSyntaxTree.ParseText(source, new CSharpParseOptions(LanguageVersion.Latest))],
        refs.Concat(ReferencesHelper.GetReferences(ReferencesSet.MessagePack)),
        new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
    var driver = CSharpGeneratorDriver.Create(new MessagePackGenerator());
    driver.RunGeneratorsAndUpdateCompilation(compilation, out Compilation outputCompilation, out _);
    return (outputCompilation, outputCompilation.GetDiagnostics());
}
// Usings already available: MessagePack.SourceGenerator, MessagePack.SourceGenerator.Tests, Microsoft.CodeAnalysis,
// Microsoft.CodeAnalysis.CSharp, Microsoft.CodeAnalysis.Testing, Xunit, System.Linq, System.Collections.Immutable.
// Note: the generator emits C# that the consumer compiles; preprocessor symbols such as NETSTANDARD2_0
// can be simulated with new CSharpParseOptions(LanguageVersion.Latest, preprocessorSymbols: new[]{"NETSTANDARD2_0"})
// applied to the output syntax trees (re-parse outputCompilation.SyntaxTrees with those options).'''

PROMPT = """You write DISPOSABLE acceptance scenarios for a code review factory (xUnit, C#).
Goal: each scenario asserts one locked acceptance criterion from the point of view of a USER of the library,
so that running it on the version before the change and on the version after the change reveals behaviour differences.
Do NOT read or trust the author's tests; derive scenarios only from the criteria and from what the diff touches.

Requirement {rid}: {title}
Locked acceptance criteria:
{criteria}

Non-mechanical diff of the change (generated snapshots omitted):
{diff}

{harness}

Write ONE C# file containing `public class CatchingTests` with 6 to 8 [Fact] methods.
Rules:
- Method name: C<n>_<AC-id with underscore>_<short_scenario>, e.g. C1_AC_3_UserResolverAlreadyAnnotated.
- Each scenario is a realistic user project source (MessagePackObject types, enums, unions, custom
  [GeneratedMessagePackResolver] partial resolvers with user-written members, nested/generic types, several targets
  simulated through preprocessor symbols) and asserts what the criterion requires (compiles without errors,
  types carry or do not carry an attribute, user-written code is not affected, etc.).
- Assertions must be about observable results (diagnostics, symbols, attributes), not about generated text formatting.
- Put a one-line comment above each [Fact]: // criterion: AC-x — what a user expects.
Output ONLY the C# file inside one ```csharp fenced block."""


def nonmech_diff(wt, base, head):
    files = [f for f in subprocess.run(["git", "-C", wt, "diff", "--name-only", base, head], capture_output=True, text=True).stdout.split("\n")
             if f and not f.endswith(".g.cs") and not f.endswith("Template.cs") and "/tests/" not in f and not f.startswith("tests/")]
    return subprocess.run(["git", "-C", wt, "diff", "-U2", base, head, "--", *files], capture_output=True, text=True).stdout[:12000]


def generate(req, wt, base, head, model):
    crit = "\n".join(f"- {c['id']}: {c['text']}" for c in req["acceptance_criteria"])
    prompt = PROMPT.format(rid=req["id"], title=req["title"], criteria=crit, diff=nonmech_diff(wt, base, head), harness=HARNESS)
    p = subprocess.run(["claude", "-p", "--model", model, "--disallowedTools", "Bash,Edit,Write,Read,WebFetch,WebSearch,Agent"],
                       input=prompt, capture_output=True, text=True, timeout=600)
    m = re.search(r"```csharp\s*(.*?)```", p.stdout, re.S)
    if not m:
        raise SystemExit("generator returned no C# block:\n" + p.stdout[:2000])
    code = m.group(1)
    head_usings = ("using MessagePack.SourceGenerator;\nusing MessagePack.SourceGenerator.Tests;\nusing Microsoft.CodeAnalysis;\n"
                   "using Microsoft.CodeAnalysis.CSharp;\nusing Microsoft.CodeAnalysis.CSharp.Syntax;\nusing Microsoft.CodeAnalysis.Testing;\n")
    # only the file header's usings (before the first other line) — never the ones inside scenario strings
    lines = code.split("\n"); k = 0
    while k < len(lines) and (lines[k].startswith("using ") or not lines[k].strip()):
        k += 1
    own = [l for l in lines[:k] if l.startswith("using ")]
    body = "\n".join(lines[k:])
    usings = sorted(set(head_usings.strip().split("\n")) | {u.strip() for u in own} |
                    {"using System.Reflection;", "using MessagePack;"})
    return "// GENERATED by catching.py — disposable, never committed.\n" + "\n".join(usings) + "\n" + body


REPEAT = 3  # anti-flaky guard: every scenario runs 3 times per side


def _one_run(wt, e, build):
    cmd = ["dotnet", "test", "tests/MessagePack.SourceGenerator.Tests", "-c", "Release",
           "--filter", "FullyQualifiedName~CatchingTests", "--logger", "console;verbosity=normal"]
    if not build:
        cmd.append("--no-build")
    p = subprocess.run(cmd, cwd=wt, capture_output=True, text=True, env=e)
    out = p.stdout + p.stderr
    res = {m.group(2): ("passes" if m.group(1) == "Passed" else "fails")
           for m in re.finditer(r"^\s+(Passed|Failed) CatchingTests\.(\w+)", out, re.M)}
    msgs = {m.group(1): " ".join(m.group(2).split())[:300]
            for m in re.finditer(r"Failed CatchingTests\.(\w+).*?Error Message:\s*\n(.*?)(?:Stack Trace|\n\s+(?:Passed|Failed) |\Z)", out, re.S)}
    return res, msgs, out


def run_side(wt, text, e, repeat=REPEAT):
    """Run the scenarios `repeat` times; a test whose outcome changes between runs is 'unstable'."""
    dest = Path(wt) / DEST
    dest.write_text(text, encoding="utf-8")
    try:
        runs, msgs, out = [], {}, ""
        for i in range(repeat):
            r, m, o = _one_run(wt, e, build=(i == 0))
            if i == 0 and not r:
                return {}, sorted(set(re.findall(r"error CS\d+: [^\[]+", o)))[:5], o, {}
            runs.append(r); msgs.update(m); out = o
        res = {}
        for name in set().union(*runs):
            seen = {r.get(name, "absent") for r in runs}
            res[name] = seen.pop() if len(seen) == 1 else "unstable"
        return res, [], out, msgs
    finally:
        dest.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--req", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="sonnet"); ap.add_argument("--reuse", action="store_true")
    a = ap.parse_args()
    req = yaml.safe_load(Path(a.req).read_text())
    repro, sb = replay.load(req['id']); e = replay.env(sb)
    for wt, ref in ((sb["worktree_base"], repro["base"]), (sb["worktree_head"], repro["head"])):
        subprocess.run(["git", "-C", wt, "checkout", "-q", "-f", ref])
    scen = HERE / "scenarios" / "CatchingTests.cs"
    t0 = time.time()
    if not (a.reuse and scen.exists()):
        scen.write_text(generate(req, sb["worktree_head"], repro["base"], repro["head"], a.model), encoding="utf-8")
    text = scen.read_text(encoding="utf-8")
    with cf.ThreadPoolExecutor(2) as ex:
        fb, fh = ex.submit(run_side, sb["worktree_base"], text, e), ex.submit(run_side, sb["worktree_head"], text, e)
        (rb, eb, ob, mb), (rh, eh, oh, mh) = fb.result(), fh.result()
    if eb or eh:
        (HERE / "out" / "catching-build.log").write_text(ob + "\n=====\n" + oh)
        raise SystemExit(f"generated scenarios do not compile (base {eb} / branch {eh}); see out/catching-build.log")
    comments = dict(re.findall(r"//\s*criterion:\s*(AC-\d+)[^\n]*\n\s*\[Fact[^\n]*\n\s*public[^\n]*?(\w+)\s*\(", text))
    rows = []
    for name in sorted(set(rb) | set(rh)):
        b, h = rb.get(name, "absent"), rh.get(name, "absent")
        branch_msg = mh.get(name) or ""
        # a crash (unexpected exception) is not a behavioural catch; an assertion or diagnostic failure is
        assertion_failure = not (re.search(r"\b\w+Exception\b", branch_msg) and not re.search(r"Assert", branch_msg))
        kind = ("UNSTABLE (never counted as a catch)" if "unstable" in (b, h) else
                "CATCH" if (b, h) == ("passes", "fails") and assertion_failure else
                "TO REVIEW (non-assertion failure)" if (b, h) == ("passes", "fails") else
                "IMPLEMENTATION PROVEN" if (b, h) == ("fails", "passes") else
                "FAILS ON BOTH SIDES" if (b, h) == ("fails", "fails") else "no information")
        crit = re.search(r"AC_(\d+)", name)
        rows.append({"test": name, "criterion": f"AC-{crit.group(1)}" if crit else None, "base": b, "branch": h, "class": kind,
                     "message_base": mb.get(name), "message_branch": mh.get(name)})
    summary = {"requirement": req["id"], "generator": f"claude -p --model {a.model}", "scenarios": len(rows),
               "catches": [r for r in rows if r["class"] == "CATCH"],
               "proven": [r for r in rows if r["class"] == "IMPLEMENTATION PROVEN"],
               "to_review": [r for r in rows if r["class"] in ("FAILS ON BOTH SIDES", "TO REVIEW (non-assertion failure)")],
               "flaky": [r for r in rows if r["class"].startswith("UNSTABLE")],
               "discarded": [r for r in rows if r["class"] == "no information"],
               "repeat": REPEAT,
               "seconds": round(time.time() - t0), "scenario_file": "scenarios/CatchingTests.cs"}
    Path(a.out, f"catching-{req['id']}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    for r in rows:
        print(f"{r['class']:24} {r['criterion'] or '-':5} base {r['base']:7} branch {r['branch']:7} {r['test']}")
    for r in summary["to_review"]:
        print(f"  to review {r['test']}: {r['message_branch']}")
    print(f"\n{len(summary['catches'])} catch(es), {len(summary['proven'])} proven, {len(summary['to_review'])} to review, {len(summary['discarded'])} with no information — {summary['seconds']} s")


if __name__ == "__main__":
    main()
