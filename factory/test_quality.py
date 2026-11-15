#!/usr/bin/env python3
"""Static checks on C# xUnit test sources (no execution).

For every [Fact]/[Theory] method:
  - criteria it declares it covers: "AC_3" in the method name, or a comment "// covers: AC-3" /
    "// criterion: AC-3" in the 3 lines above the attribute
  - assertion-strength issues:
      no assertion         no Assert./Should call at all
      trivial assertion    only Assert.NotNull / Assert.True(true) / Assert.NotEmpty
      tautology            Assert.Equal(x, x), Assert.True(true), "Count >= 0", "Length >= 0"
      text only            only checks that generated TEXT contains a string (no compile, no symbol)
"""
import re, sys
from pathlib import Path

METHOD = re.compile(r"\[(Fact|Theory)[^\]]*\]\s*(?:\[[^\]]*\]\s*)*public\s+(?:async\s+)?(?:Task|void)\s+(\w+)\s*\(", re.S)
ASSERT = re.compile(r"\bAssert\.(\w+)\s*\(|\.Should\(")
AC_NAME = re.compile(r"AC_(\d+)")
AC_COMMENT = re.compile(r"//\s*(?:covers|criterion)\s*:?\s*(AC-\d+(?:\s*,\s*AC-\d+)*)", re.I)


def _body(text, start):
    i = text.find("{", start)
    if i < 0:
        return ""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    return text[i:]


HELPER = re.compile(r"(?:private|internal|public)\s+(?:static\s+)?(?:async\s+)?[\w<>\[\],\s]+?\s+(\w+)\s*\([^)]*\)\s*\{")


def _assert_helpers(text):
    """Names of non-test methods that themselves assert (tests calling them do assert)."""
    names = set()
    for m in HELPER.finditer(text):
        if ASSERT.search(_body(text, m.end() - 1)):
            names.add(m.group(1))
    return names


def analyze(text, source="", assertion_helpers=()):
    out = []
    helpers = _assert_helpers(text)
    for m in METHOD.finditer(text):
        name = m.group(2)
        before = "\n".join(text[:m.start()].split("\n")[-4:])
        crit = {f"AC-{n}" for n in AC_NAME.findall(name)}
        for c in AC_COMMENT.findall(before):
            crit |= {x.strip().upper() for x in c.split(",")}
        body = _body(text, m.end())
        kinds = [a.group(1) or "Should" for a in ASSERT.finditer(body)]
        kinds += ["helper:" + h for h in helpers if h != name and re.search(r"\b" + h + r"\s*\(", body)]
        kinds += ["verifier"] * sum(len(re.findall(pat, body)) for pat in assertion_helpers)
        issues = []
        if not kinds:
            issues.append("no assertion")
        elif set(kinds) <= {"NotNull", "NotEmpty"} or re.search(r"Assert\.True\(\s*true\s*\)", body):
            issues.append("trivial assertion")
        if re.search(r"(Count|Length)\s*>=\s*0\b", body) or re.search(r"Assert\.True\(\s*true\s*\)", body):
            issues.append("tautology")
        for a in re.finditer(r"Assert\.Equal\(\s*([^,()]+)\s*,\s*([^,()]+)\s*\)", body):
            if a.group(1).strip() == a.group(2).strip():
                issues.append("tautology"); break
        if kinds and "verifier" not in kinds and re.search(r"\.Contains\(", body) and not re.search(r"GetDiagnostics|GetAttributes|GetTypeByMetadataName|Severity|Compilation", body):
            issues.append("text only")
        out.append({"test": name, "source": source, "criteria": sorted(crit), "assertions": len(kinds),
                    "lines": body.count("\n") + 1,
                    "issues": sorted(set(issues))})
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        for r in analyze(Path(p).read_text(encoding="utf-8"), p):
            print(f"{r['test']:60} {','.join(r['criteria']) or '-':10} asserts={r['assertions']:2} {', '.join(r['issues']) or 'ok'}")
