#!/usr/bin/env python3
"""Change Passport — reference implementation (not a product).

Builds a passport for one agent-written change:
  1. partitions the diff by the versioned policy (deterministic, no LLM)
  2. checks mechanical zones against the rule derived from the locked requirement
  3. traces every non-mechanical hunk to an agent claim (orphans are flagged)
  4. merges executed evidence, AI findings (+ their verification) and refusals
  5. computes the lane with a deterministic verdict engine and a reading contract
  6. pre-fills the attestation the named owner signs

Usage: passport.py --repo R --req REQ.yaml [--evidence E.json] [--ai A.json --verif V.json] [--head REF] --out DIR
"""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
import yaml
import test_quality

HERE = Path(__file__).parent


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *args],
                          capture_output=True, text=True, check=True).stdout


def glob_re(g):
    out, i = "", 0
    while i < len(g):
        if g.startswith("**/", i):
            out += "(?:.*/)?"; i += 3
        elif g.startswith("**", i):
            out += ".*"; i += 2
        elif g[i] == "*":
            out += "[^/]*"; i += 1
        else:
            out += re.escape(g[i]); i += 1
    return re.compile("^" + out + "$")


def parse_diff(text):
    files, cur, hunk = [], None, None
    for raw in text.split("\n"):
        line = raw.rstrip("\r")
        if line.startswith("diff --git "):
            cur = {"path": None, "hunks": []}; files.append(cur); hunk = None
        elif line.startswith("+++ "):
            p = line[4:].rstrip("\t")
            cur["path"] = p[2:] if p.startswith("b/") else cur["path"]
        elif line.startswith("--- "):
            p = line[4:].rstrip("\t")
            if p.startswith("a/"): cur["path"] = cur["path"] or p[2:]
        elif line.startswith("@@"):
            hunk = {"header": line, "added": [], "removed": []}; cur["hunks"].append(hunk)
        elif hunk is not None and line.startswith("+"):
            hunk["added"].append(line[1:])
        elif hunk is not None and line.startswith("-"):
            hunk["removed"].append(line[1:])
    return [f for f in files if f["path"]]


def zone_of(path, policy):
    for z in policy["zones"]:
        if any(glob_re(g).match(path) for g in z["globs"]):
            return z
    raise ValueError(path)


def build(args):
    policy = yaml.safe_load((HERE / "review-policy.yaml").read_text())
    trust = yaml.safe_load((HERE / "trust.yaml").read_text())["zones"]
    req = yaml.safe_load(Path(args.req).read_text())
    head = args.head or f"origin/{req['branch']}"
    base = req["base"]
    evidence_doc = json.loads(Path(args.evidence).read_text()) if args.evidence else {}
    evidence = evidence_doc.get("runs", [])
    ai = json.loads(Path(args.ai).read_text()) if args.ai else None
    verif = json.loads(Path(args.verif).read_text()) if args.verif else None

    files = parse_diff(git(args.repo, "diff", "-U0", "--no-color", base, head))
    zones_by_name = {z["name"]: z for z in policy["zones"]}
    mech = req.get("mechanical_expectation") or {}
    allowed_add = [re.compile(r) for r in mech.get("allowed_added_lines", [])]
    allowed_rem = [re.compile(r) for r in mech.get("allowed_removed_lines", [])]
    claims = req.get("claims", [])

    mech_pass, mech_flag, hunks_out, orphans = [], [], [], []
    zone_stats = {}
    total_lines = 0
    for f in files:
        z = zone_of(f["path"], policy)
        n = sum(len(h["added"]) + len(h["removed"]) for h in f["hunks"])
        total_lines += n
        st = zone_stats.setdefault(z["name"], {"zone": z["name"], "class": z["class"], "files": 0, "lines": 0,
                                               "severity": z.get("severity"), "why": z["why"],
                                               "trust": trust.get(z["name"], {}).get("level", "new")})
        st["files"] += 1; st["lines"] += n
        if z["class"] == "mechanical":
            # Generic rule: a generated file is proven if the factory regenerated it and it matched
            # (evidence of type "regeneration" covering this zone). A requirement MAY add a stricter
            # declared line rule; it never replaces regeneration.
            regen = [e for e in evidence if z["name"] in e.get("regenerates", []) and e.get("result") == "pass"]
            bad = []
            if allowed_add:
                bad = [("+", l) for h in f["hunks"] for l in h["added"] if not any(r.match(l) for r in allowed_add)]
                bad += [("-", l) for h in f["hunks"] for l in h["removed"] if not any(r.match(l) for r in allowed_rem)]
            if not regen:
                mech_flag.append({"id": f"MECH-{len(mech_flag)+1}", "file": f["path"], "lines": n,
                                  "offending": ["no regeneration evidence for this generated file"]})
            elif bad:
                mech_flag.append({"id": f"MECH-{len(mech_flag)+1}", "file": f["path"], "lines": n,
                                  "offending": [s + l[:140] for s, l in bad[:6]]})
            else:
                mech_pass.append(f["path"])
            continue
        for h in f["hunks"]:
            body = h["added"] + h["removed"]
            claim = None
            for c in claims:
                if f["path"] in c.get("trace_files", []) or any(
                        re.search(p, l) for p in c.get("trace_patterns", []) for l in body):
                    claim = c["id"]; break
            entry = {"file": f["path"], "zone": z["name"], "class": z["class"], "header": h["header"].split("@@")[1].strip(),
                     "lines": len(body), "claim": claim,
                     "preview": [("+" + l)[:160] for l in h["added"][:3]] + [("-" + l)[:160] for l in h["removed"][:2]],
                     "_add": h["added"], "_rem": h["removed"]}
            hunks_out.append(entry)

    # D1 — moved code: a block whose significant lines were removed elsewhere in the same diff
    # (whitespace ignored) is a move, not new logic. Excluded from orphans and reading, with proof.
    norm = lambda l: " ".join(l.split())
    sig = lambda ls: [norm(l) for l in ls if len(norm(l)) > 3 and norm(l) not in ("{", "}", "};")]
    moved = []
    for i, h in enumerate(hunks_out):
        a = sig(h["_add"])
        if len(a) < 3:
            continue
        pool = {}
        for j, o in enumerate(hunks_out):
            if j != i:
                for l in sig(o["_rem"]):
                    pool.setdefault(l, set()).add((o["file"], o["header"]))
        hit = [l for l in a if l in pool]
        if len(hit) >= 0.9 * len(a):
            srcs = sorted({src for l in hit for src in pool[l]})
            h["moved_from"] = [f"{f} {hd}" for f, hd in srcs][:2]
            moved.append(h)
    moved_src = {(f.split(" ", 1)[0]) for h in moved for f in h["moved_from"]}
    for h in hunks_out:
        if h.get("moved_from"):
            continue
        r = sig(h["_rem"])
        if r and not sig(h["_add"]) and h["file"] in moved_src:
            h["moved_to"] = True  # the removal side of a move
    for h in hunks_out:
        if h["claim"] is None and not h.get("moved_from") and not h.get("moved_to"):
            orphans.append(h)

    # Deterministic check derived from the requirement: every generator-owned type in the changed
    # snapshots must carry the required annotation (AC coverage, independent from the agent's tests).
    cov = req.get("coverage_check")
    if cov:
        decl = re.compile(cov["type_decl"])
        missing = []
        all_paths = [p for p in git(args.repo, "ls-tree", "-r", "--name-only", head).split("\n") if p]
        excluded = {e["path"] for e in cov.get("exclude", [])}
        for path in all_paths:
            if path in excluded or zone_of(path, policy)["name"] != cov["zone"]:
                continue
            f = {"path": path}
            try:
                txt = git(args.repo, "show", f"{head}:{f['path']}").replace("\r", "").split("\n")
            except subprocess.CalledProcessError:
                continue
            for i, l in enumerate(txt):
                if decl.search(l) and not any(re.search(cov["require"], x) for x in txt[max(0, i - 3):i]):
                    missing.append(f"{f['path']}:{i+1}: {l.strip()[:90]}")
        evidence = evidence + [{"id": "MECH-COV", "type": "mechanical", "by": "coverage rule derived from the requirement",
                                "what": f"Every generated type in every snapshot carries {cov['require']} ({len(excluded)} fixture(s) excluded with justification)",
                                "result": "pass" if not missing else "fail",
                                "detail": f"{len(missing)} type(s) without the attribute" + ("" if not missing else ": " + "; ".join(missing[:3])),
                                ("supports" if not missing else "contradicts"): cov["criteria"]}]
    weakened = []
    for h in hunks_out:
        if h["class"] == "tests":
            pass
    for f in files:
        if zone_of(f["path"], policy)["class"] != "tests":
            continue
        for h in f["hunks"]:
            gone = [l for l in h["removed"] if re.search(r"\bAssert\.|Should\(|\[Fact|\[Theory", l)]
            if gone:
                weakened.append({"file": f["path"], "header": h["header"].split("@@")[1].strip(), "removed": gone[:3]})

    # T2 — assertion strength + S2 — test <-> criterion links
    test_rows = []
    for f in files:
        if zone_of(f["path"], policy)["class"] == "tests" and f["path"].endswith(".cs"):
            try:
                txt = git(args.repo, "show", f"{head}:{f['path']}")
            except subprocess.CalledProcessError:
                continue
            for r in test_quality.analyze(txt, f["path"], policy.get("assertion_helpers", [])):
                test_rows.append({**r, "origin": "agent"})
    for extra in (getattr(args, "tests", None) or []):
        for r in test_quality.analyze(Path(extra).read_text(encoding="utf-8"), extra, policy.get("assertion_helpers", [])):
            test_rows.append({**r, "origin": "factory"})
    results = {}
    for e in evidence:
        for t in e.get("test_results", []):
            results[t["test"]] = t["branch"]
    cat_rows = []
    if getattr(args, "catching", None) and Path(args.catching).exists():
        cj = json.loads(Path(args.catching).read_text())
        for bucket in ("catches", "proven", "to_review", "discarded", "flaky"):
            for r in cj.get(bucket, []):
                results[r["test"]] = r["branch"]
                cat_rows.append(r)
    for e in evidence:  # executed scenarios declared in evidence (e.g. end-to-end) can cover criteria too
        for t in e.get("test_results", []):
            if t.get("criteria") and t["test"] not in {r["test"] for r in test_rows}:
                test_rows.append({"test": t["test"], "source": e["id"], "criteria": t["criteria"], "assertions": 1,
                                  "lines": 0, "issues": [], "origin": "factory"})
    for r in test_rows:
        r["branch"] = results.get(r["test"], "not run")
    weak_tests = [r for r in test_rows if r["issues"]]
    unlinked_agent = [r for r in test_rows if r["origin"] == "agent" and not r["criteria"]]
    if test_rows:
        claim_of_file = {}
        for c in claims:
            for tf in c.get("trace_files", []):
                claim_of_file[tf] = c["id"]
        affected = sorted({claim_of_file[r["source"]] for r in weak_tests + unlinked_agent if r["source"] in claim_of_file})
        evidence = evidence + [{"id": "TEST-QUALITY", "type": "test-strength", "by": "static analysis of the tests (test_quality.py)",
                                "what": f"Assertion strength and test → criterion links across {len(test_rows)} tests",
                                "result": "weak" if (weak_tests or unlinked_agent) else "pass",
                                "detail": "; ".join([f"{r['test']}: {', '.join(r['issues'])}" for r in weak_tests][:4]
                                                    + ([f"{len(unlinked_agent)} agent test(s) linked to no criterion"] if unlinked_agent else [])) or "no issue",
                                "affects": affected}]

    # Claims and criteria status from evidence
    def ev_for(key, rel):
        return [e for e in evidence if key in e.get(rel, [])]
    claims_out = []
    for c in claims:
        sup, con, aff = ev_for(c["id"], "supports"), ev_for(c["id"], "contradicts"), ev_for(c["id"], "affects")
        status = "contradicted" if con else ("proven" + (" (weak evidence)" if aff else "") if sup else "unproven")
        claims_out.append({**{k: c[k] for k in ("id", "text")}, "status": status,
                           "evidence": [e["id"] for e in sup + con + aff]})
    criteria_out = []
    for ac in req.get("acceptance_criteria", []):
        sup, con = ev_for(ac["id"], "supports"), ev_for(ac["id"], "contradicts")
        linked = [{"test": r["test"], "origin": r["origin"], "branch": r["branch"], "issues": r["issues"]}
                  for r in test_rows if ac["id"] in r["criteria"]]
        good = [t for t in linked if t["branch"] == "passes" and not t["issues"]]
        if con:
            status = "contradicted"
        elif sup and good:
            status = "supported"
        elif sup:
            status = "supported without a passing linked test"
        else:
            status = "not demonstrated"
        criteria_out.append({**ac, "status": status, "evidence": [e["id"] for e in sup + con], "tests": linked})

    # Findings (AI) with verification
    findings = []
    if ai:
        vmap = {v["finding"]: v for v in (verif or {}).get("verdicts", [])}
        for fd in ai["findings"]:
            v = vmap.get(fd["id"])
            findings.append({**fd, "verification": v["status"] if v else "opinion (unverified)",
                             "verification_evidence": v["evidence"] if v else [], "verification_note": v.get("note") if v else None})
    missed = (verif or {}).get("missed_by_ai", [])

    # Refusals: rules + evidence + AI
    cat = policy["refusal_catalog"]
    refusals = []
    def add_ref(kind, question, why, source):
        r = cat[kind]
        refusals.append({"id": f"R{len(refusals)+1}", "kind": kind, "severity": r["severity"], "decider": r["decider"],
                         "question": question, "why": why, "source": source})
    for st in zone_stats.values():
        if st["zone"] == "public-api":
            add_ref("public-api", "Approve the shape and naming of the added public API", "Public contract, irreversible once published", "zone rule")
        if st["zone"] == "diagnostics":
            add_ref("diagnostic-ids", "Approve the allocation of the new diagnostic IDs", "Public, permanent identifiers", "zone rule")
    for e in evidence:
        for r in e.get("refusals", []):
            add_ref(r["kind"], r["question"], r["why"], "evidence " + e["id"])
    if ai:
        resolved = {r["refusal"] for r in (verif or {}).get("refusals_resolved_by_evidence", [])}
        for r in ai.get("refusals", []):
            if r["id"] not in resolved:
                add_ref(r.get("kind", "unproven-claim"), r["question"], r["why_refused"], f"AI reviewer ({r['id']})")
    for c in claims_out:
        if c["status"] == "unproven":
            add_ref("unproven-claim", f"Accept claim {c['id']} without evidence: “{c['text']}”", "No executed or mechanical evidence", "rule")

    # Verdict engine (deterministic, explainable)
    non_mech_lines = sum(h["lines"] for h in hunks_out)
    reasons_red, reasons_orange = [], []
    for ac in criteria_out:
        if ac["status"] == "contradicted":
            reasons_red.append(f"{ac['id']} contradicted by {', '.join(ac['evidence'])}: {ac['text']}")
    for st in zone_stats.values():
        if st["class"] == "sensitive" and st.get("severity") == "major":
            reasons_red.append(f"zone {st['zone']} touched ({st['why']})")
    for r in refusals:
        if r["severity"] == "major":
            reasons_red.append(f"open major refusal {r['id']}: {r['question']}")
    if non_mech_lines > policy["limits"]["max_non_mechanical_changed_lines"]:
        reasons_red.append(f"{non_mech_lines} non-mechanical lines > {policy['limits']['max_non_mechanical_changed_lines']}")
    for st in zone_stats.values():
        if st["class"] in ("sensitive", "derived"):
            reasons_orange.append(f"sensitive zone {st['zone']} touched")
        if st["trust"] != "trusted":
            reasons_orange.append(f"zone {st['zone']} not trusted yet ({st['trust']})")
    for o in orphans:
        reasons_orange.append(f"orphan hunk (no claim): {o['file']} {o['header']}")
    for m in mech_flag:
        reasons_orange.append(f"{m['id']} mechanical file outside the rule: {m['file']}")
    for w in weakened:
        reasons_orange.append(f"assertion or test removed in {w['file']} {w['header']}")
    for ac in criteria_out:
        if ac["status"] in ("supported without a passing linked test", "not demonstrated"):
            reasons_orange.append(f"criterion {ac['id']} {ac['status']}")
    for r in weak_tests:
        if r["origin"] == "agent":
            reasons_orange.append(f"weak agent test: {r['test']} ({', '.join(r['issues'])})")
    for c in claims_out:
        if c["status"] != "proven":
            reasons_orange.append(f"claim {c['id']} {c['status']}")
    for r in refusals:
        if r["severity"] == "minor":
            reasons_orange.append(f"refusal {r['id']}: {r['question']}")
    lane = "RED" if reasons_red else ("ORANGE" if reasons_orange else "GREEN")
    lane_def = next(l for l in policy["lanes"] if l["lane"] == lane)
    action = lane_def["action"]
    if any("contradicted" in r for r in reasons_red):
        action = "Do not sign as is: send back to the agent with the evidence (the owner confirms)"

    # Reading contract
    must_read = []
    for h in hunks_out:
        if h["class"] == "derived":
            continue  # covered by the .tt + snapshot rule
        if h["class"] in ("sensitive", "ordinary") or h["claim"] is None:
            must_read.append({"file": h["file"], "header": h["header"], "lines": h["lines"],
                              "why": "orphan" if h["claim"] is None else f"zone {h['zone']}"})
    for m in mech_flag:
        must_read.append({"file": m["file"], "header": "whole file", "lines": m["lines"], "why": f"{m['id']} outside the mechanical rule"})
    for w in weakened:
        must_read.append({"file": w["file"], "header": w["header"], "lines": len(w["removed"]), "why": "assertion removed"})
    changed_in = {f["path"]: sum(len(h["added"]) + len(h["removed"]) for h in f["hunks"]) for f in files}
    for r in weak_tests:
        if r["origin"] != "agent":
            continue
        already = any(m["file"] == r["source"] for m in must_read)
        # a weak test is pointed out, but its lines are only counted if the file is not already read
        must_read.append({"file": r["source"], "header": r["test"], "lines": 0 if already else min(r["lines"], changed_in.get(r["source"], r["lines"])),
                          "why": f"weak test: {', '.join(r['issues'])}" + (" (lines already counted)" if already else "")})
        changed_in[r["source"]] = 0  # never count the same file's lines twice
    must_read = [m for m in must_read if not any(h.get("moved_from") or h.get("moved_to")
                 for h in hunks_out if h["file"] == m["file"] and h["header"] == m["header"])]
    # D3 — sort by risk: what is most likely to hide a defect comes first
    sev = {z["name"]: z.get("severity") for z in policy["zones"]}
    def score(m):
        w = m["why"]
        if w.startswith("orphan") or "outside the mechanical rule" in w or "assertion removed" in w:
            return 0
        if w.startswith("weak test"):
            return 1
        zone = w.replace("zone ", "")
        return 2 if sev.get(zone) == "major" else 3 if sev.get(zone) == "minor" else 4
    must_read.sort(key=lambda m: (score(m), m["file"], m["header"]))
    test_files = sorted({h["file"] for h in hunks_out if h["class"] == "tests"})
    lines_to_read = sum(x["lines"] for x in must_read)
    derived = [h for h in hunks_out if h["class"] == "derived"]
    excluded = []
    if mech_pass:
        regen_ids = sorted({e["id"] for e in evidence if e.get("regenerates") and e.get("result") == "pass"})
        excluded.append({"what": f"{len(mech_pass)} generated files", "lines":
                         sum(len(h["added"]) + len(h["removed"]) for f in files if f["path"] in set(mech_pass) for h in f["hunks"]),
                         "why": "regenerated by the factory from their source: identical to the committed ones",
                         "proof": "evidence " + ", ".join(regen_ids) + (" + declared rule: " + " | ".join(r.pattern for r in allowed_add) if allowed_add else "")})
    if derived:
        dz = {h["zone"] for h in derived}
        excluded.append({"kind": "derived", "what": f"{len({h['file'] for h in derived})} files derived from a source", "lines": sum(h["lines"] for h in derived),
                         "why": "read through their source (" + "; ".join(zones_by_name[z]["why"] for z in dz) + ")",
                         "proof": "policy zone(s) " + ", ".join(sorted(dz))})
    mv = [h for h in hunks_out if h.get("moved_from") or h.get("moved_to")]
    if mv:
        excluded.append({"what": f"{len(mv)} moved blocks", "lines": sum(h["lines"] for h in mv),
                         "why": "identical code (whitespace ignored) removed elsewhere in the same diff",
                         "proof": "; ".join(f"{h['file']} {h['header']} ← {h['moved_from'][0]}" for h in mv if h.get("moved_from"))[:300]})
    tests_ok = [h for h in hunks_out if h["class"] == "tests" and not any(m["file"] == h["file"] for m in must_read)]
    if tests_ok:
        excluded.append({"what": f"{len({h['file'] for h in tests_ok})} test file(s)", "lines": sum(h["lines"] for h in tests_ok),
                         "why": "summarised by the evidence (execution, assertion strength, links to criteria)", "proof": "TEST-QUALITY + executed evidence"})

    # Attestation draft
    checked = [{"what": f"{len(mech_pass)} generated files identical after regeneration", "by": "regeneration in the sandbox"}] if mech_pass else []
    for e in evidence:
        checked.append({"what": f"{e['what']} → {e['result']}", "by": e["by"], "id": e["id"]})
    for f in findings:
        checked.append({"what": f"{f['id']} {f['title']} → {f['verification']}", "by": "AI reviewer + verification", "id": f["id"]})
    checked.append({"what": f"{len(must_read)} reading-contract hunks ({lines_to_read} lines)", "by": "owner (to tick)"})
    not_checked = []
    for x in excluded:
        if x.get("kind") == "derived":
            not_checked.append({"what": x["what"], "why": x["why"]})
    for c in claims_out:
        if c["status"] == "unproven":
            not_checked.append({"what": f"Claim {c['id']}: {c['text']}", "why": "no executed or mechanical evidence"})
    for ac in criteria_out:
        if ac["status"] in ("supported without a passing linked test", "not demonstrated"):
            not_checked.append({"what": f"Criterion {ac['id']} by a linked test", "why": ac["status"]})
    not_checked += evidence_doc.get("not_checked", [])
    if not any(e.get("type", "").startswith("executed") for e in evidence):
        not_checked.append({"what": "Execution of the change", "why": "no executed evidence provided for this change"})

    for h in hunks_out:
        h.pop("_add", None); h.pop("_rem", None)
    passport = {
        "schema": "change-passport/2",
        "change": {"branch": req.get("branch"), "base": base, "head": git(args.repo, "rev-parse", "--short", head).strip(),
                   "files": len(files), "changed_lines": total_lines},
        "requirement": {k: req.get(k) for k in ("id", "title", "source", "owner", "policy_guardian")},
        "acceptance_criteria": criteria_out,
        "claims": claims_out,
        "zones": sorted(zone_stats.values(), key=lambda s: -s["lines"]),
        "mechanical": {"rule": [r.pattern for r in allowed_add], "passed": len(mech_pass), "flagged": mech_flag},
        "traceability": {"hunks": len(hunks_out), "traced": len(hunks_out) - len(orphans), "orphans": orphans},
        "evidence": evidence,
        "findings": findings,
        "missed_by_ai": missed,
        "weakened_tests": weakened,
        "refusals": refusals,
        "verdict": {"lane": lane, "action": action, "reasons_red": reasons_red, "reasons_orange": reasons_orange},
        "tests": test_rows + [{"test": r["test"], "origin": "catching", "criteria": [r["criterion"]] if r.get("criterion") else [],
                               "branch": r["branch"], "issues": [], "class": r["class"]} for r in cat_rows if r["test"] not in {t["test"] for t in test_rows}],
        "reading_contract": {"must_read": must_read, "excluded": excluded, "test_files_summarised": test_files,
                             "lines_to_read": lines_to_read, "lines_total": total_lines,
                             "files_to_read": len({x["file"] for x in must_read}), "files_total": len(files)},
        "attestation_draft": {"checked": checked, "not_checked": not_checked,
                              "decisions": [{"refusal": r["id"], "question": r["question"], "decision": None} for r in refusals],
                              "residual_risk": None, "signed_by": None, "date": None},
    }
    blob = json.dumps(passport, ensure_ascii=False, sort_keys=True).encode()
    passport["fingerprint"] = hashlib.sha256(blob).hexdigest()[:16]
    return passport


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True); ap.add_argument("--req", required=True)
    ap.add_argument("--evidence"); ap.add_argument("--ai"); ap.add_argument("--verif"); ap.add_argument("--head")
    ap.add_argument("--tests", nargs="*", help="reviewer-side test files (acceptance, catching) to analyse")
    ap.add_argument("--catching", help="catching results JSON")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    p = build(a)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    name = p["requirement"]["id"]
    (out / f"{name}.passport.json").write_text(json.dumps(p, ensure_ascii=False, indent=2))
    rc, v = p["reading_contract"], p["verdict"]
    print(f"{name}: lane {v['lane']} — {p['change']['files']} files / {rc['lines_total']} lines; "
          f"to read {rc['files_to_read']} files / {rc['lines_to_read']} lines; "
          f"mechanical {p['mechanical']['passed']} ok, {len(p['mechanical']['flagged'])} flagged; "
          f"orphans {len(p['traceability']['orphans'])}; refusals {len(p['refusals'])}")


if __name__ == "__main__":
    main()
