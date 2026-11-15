#!/usr/bin/env python3
"""Run the whole Change Passport pipeline on one agent change, live, end to end.

  python3 pipeline.py --req REQ-2283            # console

Steps (each one logged to out/live/<REQ>/status.json so a page can follow it):
  1 Sort     policy zones, orphan code, provisional lane         (deterministic, no evidence yet)
  2 Prove    every replayable proof, base vs branch, 3 runs each (execution)
  3 Evidence proofs turned into evidence entries                (deterministic rules)
  4 Review   a second model reviews the diff, without seeing the proofs  (LLM — recorded)
  5 Verify   quotes checked against the code; findings matched to proofs (deterministic)
  6 Passport final lane, reading contract, attestation draft     (deterministic)

The requirement (criteria, claims) is written by a human beforehand and is an input, never generated here.
Evidence that cannot be replayed live (e.g. the full test suite, ~4 min) is reused from the recorded
evidence file and labelled as reused — exactly like reusing a CI result.
"""
import argparse, datetime, json, re, subprocess, sys, time
from pathlib import Path
import yaml

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import replay

GOOD_STATUS = re.compile(r"^(passes|ran)$")


class Run:
    STEPS = [("sort", "Sort the change"), ("prove", "Run the proofs, before vs after"), ("evidence", "Turn results into evidence"),
             ("review", "AI review (a second model, blind to the proofs)"), ("verify", "Check the AI against code and proofs"),
             ("passport", "Compute the passport")]

    def __init__(self, req):
        self.req, self.dir = req, HERE / "out" / "live" / req
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state = {"requirement": req, "started": now(), "done": False, "error": None,
                      "steps": [{"id": i, "title": t, "state": "waiting", "lines": [], "seconds": None} for i, t in self.STEPS]}
        self.save()

    def step(self, sid):
        return next(s for s in self.state["steps"] if s["id"] == sid)

    def start(self, sid):
        s = self.step(sid); s["state"] = "running"; s["_t0"] = time.time(); self.save(); self.say(f"── {s['title']}")

    def log(self, sid, line):
        self.step(sid)["lines"].append(line); self.save(); self.say("   " + line)

    def end(self, sid, state="done"):
        s = self.step(sid); s["state"] = state; s["seconds"] = round(time.time() - s.pop("_t0", time.time())); self.save()

    def save(self):
        clean = json.loads(json.dumps(self.state, default=str))
        for s in clean["steps"]:
            s.pop("_t0", None)
        (self.dir / "status.json").write_text(json.dumps(clean, ensure_ascii=False, indent=1), encoding="utf-8")

    @staticmethod
    def say(msg):
        print(msg, flush=True)


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def sh(*cmd, **kw):
    return subprocess.run(list(cmd), capture_output=True, text=True, **kw)


def side_ok(side, spec):
    if not GOOD_STATUS.match(side["status"]):
        return False
    bad = spec.get("bad_regex")
    return not (bad and any(re.search(bad, l) for l in side.get("lines", [])))


def to_evidence(eid, spec, res):
    """Deterministic rule: before/after outcome -> evidence result and what it supports or contradicts."""
    b, h = res["base"], res["branch"]
    if "unstable" in (b["status"], h["status"]):
        result = "unstable"
    else:
        result = {(False, True): "fail-before", (True, True): "pass", (True, False): "regression", (False, False): "fails-both"}[
            (side_ok(b, spec), side_ok(h, spec))]
    crit = spec.get("criteria", [])
    e = {"id": eid, "type": "executed-e2e" if spec["kind"].startswith("e2e") else "executed",
         "by": f"Live sandbox replay ({spec['kind']}), base vs branch, {res.get('repeat', 1)} runs per side",
         "what": spec["title"], "result": result,
         "detail": f"Base: {b['status']}. Branch: {h['status']}. " + "; ".join(h.get("lines", [])[:4]),
         "replayed_at": res["replayed_at"]}
    # link each executed test to the criteria it was written for (what the passport calls a "linked test")
    if spec["kind"].startswith("e2e"):
        e["test_results"] = [{"test": Path(spec["scenario"]["file"]).stem, "base": "passes" if side_ok(b, spec) else "fails",
                              "branch": "passes" if side_ok(h, spec) else "fails", "criteria": crit}]
    else:
        def per_test(side):
            return {m.group(2).split(".")[-1]: ("passes" if m.group(1) == "Passed" else "fails")
                    for m in (re.match(r"\s*(Passed|Failed) ([\w.]+)", l) for l in side.get("lines", [])) if m}
        tb, th = per_test(b), per_test(h)
        e["test_results"] = [{"test": t, "base": tb.get(t, "not run"), "branch": th[t], "criteria": crit} for t in th]
    if result in ("fail-before", "pass"):
        e["supports"] = crit
    elif result in ("regression", "fails-both"):
        e["contradicts"] = crit
    return e


def git_diff(repo, base, head, limit=40000):
    return sh("git", "-C", str(repo), "diff", "-U3", base, head).stdout[:limit]


REVIEW_PROMPT = """You are a code reviewer for a change written by an AI agent. You are a different model from the author.
You review READ-ONLY: you cannot run anything and you do not see any test or execution result.

Requirement {rid}: {title}
Acceptance criteria (written by a human before the change):
{criteria}
Claims made by the agent:
{claims}

Rules:
- Each finding MUST quote the exact code it is about (copied verbatim from the diff, without the leading +/-).
- Say which criteria or claims (ids) each finding affects. Give a confidence between 0 and 1.
- Refuse, instead of deciding, anything that belongs to a person: public API shape, user-visible behaviour,
  compatibility scope, accepting a risk, or a claim you cannot check by reading. Put those in "refusals".
- No style nits. At most 6 findings. If you find nothing serious, return an empty list.

Answer with ONE JSON object and nothing else:
{{"findings":[{{"id":"F1","lens":"correctness|compatibility|test quality|security","severity":"high|medium|low",
"title":"...","file":"path","line":0,"quote":"...","affects":["AC-1"],"confidence":0.5}}],
"refusals":[{{"id":"AI-R1","question":"...","why_refused":"...","decider":"named owner|maintainer","kind":"public-api|user-visible-behaviour|compat-scope|unproven-claim"}}]}}

The diff:
{diff}
"""


def ai_review(req_doc, diff, model):
    prompt = REVIEW_PROMPT.format(
        rid=req_doc["id"], title=req_doc["title"],
        criteria="\n".join(f"- {c['id']}: {c['text']}" for c in req_doc.get("acceptance_criteria", [])),
        claims="\n".join(f"- {c['id']}: {c['text']}" for c in req_doc.get("claims", [])) or "- (none declared)", diff=diff)
    p = subprocess.run(["claude", "-p", "--model", model, "--disallowedTools", "Bash,Edit,Write,Read,WebFetch,WebSearch,Agent"],
                       input=prompt, capture_output=True, text=True, timeout=600)
    m = re.search(r"\{.*\}", p.stdout, re.S)
    if not m:
        raise RuntimeError("AI reviewer returned no JSON: " + (p.stdout or p.stderr)[:300])
    out = json.loads(m.group(0))
    return {"reviewer": f"claude -p --model {model}", "mode": "read-only, diff + requirement only, no execution, blind to the proofs",
            "reviewed_at": now(), "findings": out.get("findings", []), "refusals": out.get("refusals", [])}


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def verify(ai, evidence, repo, base, head):
    """Deterministic: a finding counts only if its quote exists, and is confirmed only by a proof that agrees."""
    verdicts, covered = [], set()
    for f in ai["findings"]:
        texts = [sh("git", "-C", str(repo), "show", f"{ref}:{f.get('file', '')}").stdout for ref in (head, base)]
        lines = [norm(l.lstrip("+-")) for l in f.get("quote", "").splitlines() if norm(l.lstrip("+-"))]
        found = bool(lines) and all(any(l in norm(t) for t in texts) for l in lines)
        aff = set(f.get("affects", []))
        against = [e["id"] for e in evidence if aff & set(e.get("contradicts", []))]
        for_ = [e["id"] for e in evidence if aff and aff <= set(e.get("supports", []))]
        if not found:
            v = {"status": "rejected — quote not found in the code", "evidence": [], "note": "Possible hallucination: never shown as a fact."}
        elif against:
            v = {"status": "confirmed", "evidence": against, "note": "A proof shows the same problem."}
            covered.update(against)
        elif for_:
            v = {"status": "opinion — proofs disagree", "evidence": for_, "note": "Executed proofs show the affected criteria hold; kept for the owner to judge."}
        else:
            v = {"status": "opinion (unverified)", "evidence": [], "note": "Quote found; no proof covers it."}
        verdicts.append({"finding": f["id"], **v})
    missed = [{"id": f"M{i+1}", "what": e["what"], "evidence": [e["id"]], "note": f"Proof result: {e['result']}; no AI finding pointed at it."}
              for i, e in enumerate(e for e in evidence if e.get("contradicts") and e["id"] not in covered)]
    return {"method": "Quote must exist in base or branch; a finding is confirmed only by a proof contradicting the same criterion.",
            "verdicts": verdicts, "missed_by_ai": missed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--req", required=True)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--skip-review", action="store_true", help="reuse the last recorded AI review (offline demo)")
    a = ap.parse_args()
    run_pipeline(a.req, a.model, a.skip_review)


def run_pipeline(req, model="sonnet", skip_review=False):
    R = Run(req)
    n = req.split("-")[1]
    repo = (HERE / "../upstream-repo").resolve()
    req_file = HERE / "requirements" / f"{req}.yaml"
    req_doc = yaml.safe_load(req_file.read_text(encoding="utf-8"))
    repro = yaml.safe_load((HERE / f"repro-{req}.yaml").read_text(encoding="utf-8"))
    base, head = repro["base"], repro["head"]
    try:
        # 1 · Sort (no evidence yet)
        R.start("sort")
        pre = R.dir / "pre"; pre.mkdir(exist_ok=True)
        p = sh(sys.executable, str(HERE / "passport.py"), "--repo", str(repo), "--req", str(req_file), "--out", str(pre))
        if p.returncode:
            raise RuntimeError(p.stderr[-400:])
        pp = json.loads((pre / f"{req}.passport.json").read_text())
        R.log("sort", f"{pp['change']['files']} files, {pp['change']['changed_lines']} lines changed")
        for z in pp["zones"]:
            R.log("sort", f"zone {z['zone']} ({z['class']}): {z['files']} files, {z['lines']} lines")
        R.log("sort", f"orphan hunks: {len(pp['traceability']['orphans'])} of {pp['traceability']['hunks']}")
        R.log("sort", f"provisional lane without proofs: {pp['verdict']['lane']} · {pp['reading_contract']['lines_to_read']} lines to read")
        R.state["provisional"] = {"lane": pp["verdict"]["lane"], "lines_to_read": pp["reading_contract"]["lines_to_read"],
                                  "lines_total": pp["reading_contract"]["lines_total"]}
        R.end("sort")

        # 2 · Prove
        R.start("prove")
        results = {}
        for eid, spec in repro["evidence"].items():
            R.log("prove", f"{eid} · {spec['title']}")
            res = replay.replay(eid, None, req)
            (R.dir / f"replay-{eid}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            results[eid] = res
            R.log("prove", f"   base: {res['base']['status']} ({'/'.join(res['base'].get('runs', []))}) · branch: {res['branch']['status']} ({'/'.join(res['branch'].get('runs', []))}) · {max(res['base']['seconds'], res['branch']['seconds'])}s (both sides in parallel)")
        R.end("prove")

        # 3 · Evidence
        R.start("evidence")
        evidence = [to_evidence(eid, repro["evidence"][eid], res) for eid, res in results.items()]
        for e in evidence:
            R.log("evidence", f"{e['id']}: {e['result']}" + (f" → supports {', '.join(e['supports'])}" if e.get("supports") else "")
                  + (f" → contradicts {', '.join(e['contradicts'])}" if e.get("contradicts") else ""))
        recorded = HERE / "evidence" / f"{n}.json"
        not_checked = []
        if recorded.exists():
            rec = json.loads(recorded.read_text(encoding="utf-8"))
            live_ids = {e["id"] for e in evidence}
            for e in rec["runs"]:
                if e["id"] not in live_ids:
                    evidence.append({**e, "by": e["by"] + " — reused (recorded run, not replayed live)"})
                    R.log("evidence", f"{e['id']}: {e['result']} (reused from the recorded run: {e['what'][:70]})")
            not_checked = rec.get("not_checked", [])
        ev_doc = {"change": repro["head"], "environment": "live pipeline run " + now(), "runs": evidence, "not_checked": not_checked}
        ev_file = R.dir / "evidence.json"
        ev_file.write_text(json.dumps(ev_doc, ensure_ascii=False, indent=1), encoding="utf-8")
        R.end("evidence")

        # 4 · AI review
        R.start("review")
        ai_file = R.dir / "ai-review.json"
        if skip_review and ai_file.exists():
            ai = json.loads(ai_file.read_text()); R.log("review", f"reusing recorded review from {ai.get('reviewed_at')}")
        else:
            R.log("review", f"reviewer: claude -p --model {model}, sees the diff and the requirement, not the proofs")
            ai = ai_review(req_doc, git_diff(repo, base, head), model)
            ai_file.write_text(json.dumps(ai, ensure_ascii=False, indent=1), encoding="utf-8")
        for f in ai["findings"]:
            R.log("review", f"{f['id']} [{f.get('severity')}] {f['title']}")
        for r in ai["refusals"]:
            R.log("review", f"refuses: {r['question']}")
        if not ai["findings"] and not ai["refusals"]:
            R.log("review", "no findings, no refusals")
        R.end("review")

        # 5 · Verify
        R.start("verify")
        ver = verify(ai, evidence, repo, base, head)
        ver_file = R.dir / "ai-verification.json"
        ver_file.write_text(json.dumps(ver, ensure_ascii=False, indent=1), encoding="utf-8")
        for v in ver["verdicts"]:
            R.log("verify", f"{v['finding']}: {v['status']}" + (f" ({', '.join(v['evidence'])})" if v["evidence"] else ""))
        for m in ver["missed_by_ai"]:
            R.log("verify", f"missed by the AI: {m['what'][:90]} ({m['evidence'][0]})")
        R.end("verify")

        # 6 · Passport
        R.start("passport")
        outd = R.dir / "passport"; outd.mkdir(exist_ok=True)
        p = sh(sys.executable, str(HERE / "passport.py"), "--repo", str(repo), "--req", str(req_file), "--evidence", str(ev_file),
               "--ai", str(ai_file), "--verif", str(ver_file), "--out", str(outd))
        if p.returncode:
            raise RuntimeError(p.stderr[-400:])
        pj = outd / f"{req}.passport.json"
        sh(sys.executable, str(HERE / "render.py"), str(pj))
        final = json.loads(pj.read_text())
        # publish next to the other passports so the demo and its links pick it up
        (HERE / "out" / f"{req}.live.passport.json").write_text(pj.read_text(), encoding="utf-8")
        html = outd / f"{req}.html"
        if html.exists():
            (HERE / "out" / f"{req}.live.html").write_text(html.read_text(), encoding="utf-8")
        rc, v = final["reading_contract"], final["verdict"]
        R.log("passport", f"lane {v['lane']} · {rc['lines_to_read']} of {rc['lines_total']} lines to read · {len(final['refusals'])} decisions for a human")
        for c in final["acceptance_criteria"]:
            R.log("passport", f"{c['id']}: {c['status']}")
        R.log("passport", "action: " + v["action"])
        R.state["final"] = {"lane": v["lane"], "lines_to_read": rc["lines_to_read"], "lines_total": rc["lines_total"],
                            "refusals": len(final["refusals"]), "page": f"{req}.live.html", "fingerprint": final["fingerprint"]}
        R.end("passport")
    except Exception as ex:
        running = next((s for s in R.state["steps"] if s["state"] == "running"), None)
        if running:
            R.log(running["id"], f"ERROR {type(ex).__name__}: {ex}"); R.end(running["id"], "failed")
        R.state["error"] = f"{type(ex).__name__}: {ex}"
    R.state["done"] = True; R.state["finished"] = now(); R.save()
    return R.state


if __name__ == "__main__":
    main()
