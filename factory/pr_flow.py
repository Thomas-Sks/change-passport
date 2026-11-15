#!/usr/bin/env python3
"""Put the Change Passport into a real pull-request flow (GitHub, via the gh CLI).

  python3 pr_flow.py publish --repo OWNER/NAME [REQ-2297 ...]
      For each REQ: find the open PR whose head is the passport's branch, post (or update)
      the passport as a PR comment, and set two commit statuses on the PR head:
        passport/lane            informational: lane + lines to read
        passport/owner-signature pending until a named owner signs

  python3 pr_flow.py sign --repo OWNER/NAME REQ-2297 --by "Camille Durand (synthetic)" \
      --decision send-back --risk "..." [--answer R1=accept ...] [--full-read]
      Writes out/signatures/<REQ>-<sha>.json (bound to the PR head commit and the passport
      fingerprint), posts it as a PR comment and resolves passport/owner-signature.

Rules enforced at signing time (the AI never signs, the script never decides for the owner):
  - the PR head must be the commit the passport was computed on (otherwise: re-run the passport);
  - every refusal of the passport needs an explicit answer from the owner;
  - accepting a RED change requires --full-read (RED means "read everything", not "sign faster").
"""
import argparse, datetime, hashlib, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "out"
MARK = "<!-- change-passport -->"
LANE_ICON = {"GREEN": "🟢", "ORANGE": "🟠", "RED": "🔴"}
DECISIONS = {"accept": ("success", "accepted"), "send-back": ("failure", "sent back to the agent"),
             "reject": ("failure", "rejected")}


def gh(*args, data=None):
    r = subprocess.run(["gh", *args], input=json.dumps(data) if data is not None else None,
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed: {r.stderr.strip()}")
    return json.loads(r.stdout) if r.stdout.strip() else None


def passport(req):
    return json.loads((OUT / f"{req}.passport.json").read_text(encoding="utf-8"))


def find_pr(repo, branch):
    prs = gh("api", f"repos/{repo}/pulls?state=open&head={repo.split('/')[0]}:{branch}")
    if not prs:
        sys.exit(f"no open PR with head {branch} in {repo}")
    return prs[0]


def cut(s, n=160):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def comment_md(p):
    v, rc, req, ch = p["verdict"], p["reading_contract"], p["requirement"], p["change"]
    L = [MARK, f"## {LANE_ICON.get(v['lane'], '')} Change Passport · {req['id']} · lane **{v['lane']}**", "",
         f"> The AI advises with evidence and never approves. **{req['owner'].split(' — ')[0]}** signs; "
         f"`passport/owner-signature` stays pending until then.", "",
         f"**Action:** {v['action']}  ",
         f"**Read:** {rc['lines_to_read']} of {rc['lines_total']} changed lines "
         f"({rc['files_to_read']} of {rc['files_total']} files) · computed on `{ch['head']}` · "
         f"fingerprint `{p['fingerprint']}`", ""]
    if v.get("reasons_red"):
        L += ["**Why RED**", *[f"- {cut(r, 220)}" for r in v["reasons_red"]], ""]
    L += ["### Acceptance criteria", "| | Criterion | Status | Evidence |", "|---|---|---|---|"]
    for c in p["acceptance_criteria"]:
        L.append(f"| {c['id']} | {cut(c['text'], 110)} | {c['status']} | {', '.join(c['evidence']) or '—'} |")
    L += ["", "### Must read", *[f"- `{m['file']}` {m['header']} · {m['lines']} lines · {m['why']}"
                                   for m in rc["must_read"][:15]]]
    if len(rc["must_read"]) > 15:
        L.append(f"- … {len(rc['must_read']) - 15} more in the full passport")
    L += ["", "### What the AI found (verified against evidence)"]
    for f in p["findings"]:
        L.append(f"- **{f['id']}** [{f['severity']}] {cut(f['title'], 150)} → *{f['verification']}*"
                 + (f" ({', '.join(f.get('verification_evidence') or [])})" if f.get("verification_evidence") else ""))
    for m in p.get("missed_by_ai", []):
        L.append(f"- **{m['id']} missed by the AI:** {cut(m['what'])} (proved by {', '.join(m['evidence'])})")
    L += ["", "### What the AI refused to decide (the owner answers each one)"]
    for r in p["refusals"]:
        L.append(f"- [ ] **{r['id']}** [{r['severity']}] {cut(r['question'], 180)}")
    L += ["", "<details><summary>Evidence ({})</summary>".format(len(p["evidence"])), "",
          "| | By | What | Result |", "|---|---|---|---|"]
    for e in p["evidence"]:
        L.append(f"| {e['id']} | {e['by']} | {cut(e['what'], 120)} | {e.get('result', '')} {cut(e.get('detail', ''), 60)} |")
    L += ["", "</details>", "", "<details><summary>Not checked</summary>", "",
          *[f"- {cut(n['what'])}: {cut(n['why'])}" for n in p["attestation_draft"]["not_checked"]],
          "", "</details>"]
    return "\n".join(L)


def upsert_comment(repo, num, body):
    for c in gh("api", f"repos/{repo}/issues/{num}/comments") or []:
        if c["body"].startswith(MARK):
            return gh("api", "-X", "PATCH", f"repos/{repo}/issues/comments/{c['id']}", "--input", "-", data={"body": body})
    return gh("api", f"repos/{repo}/issues/{num}/comments", "--input", "-", data={"body": body})


def status(repo, sha, context, state, desc, url=None):
    d = {"state": state, "context": context, "description": desc[:140]}
    if url:
        d["target_url"] = url
    gh("api", f"repos/{repo}/statuses/{sha}", "--input", "-", data=d)


def publish(repo, reqs):
    for req in reqs:
        p = passport(req)
        pr = find_pr(repo, p["change"]["branch"])
        sha = pr["head"]["sha"]
        if not sha.startswith(p["change"]["head"]):
            print(f"{req}: PR head {sha[:8]} != passport head {p['change']['head']}: passport is stale")
            status(repo, sha, "passport/owner-signature", "error", "Passport computed on another commit: re-run it")
            continue
        c = upsert_comment(repo, pr["number"], comment_md(p))
        v, rc = p["verdict"], p["reading_contract"]
        status(repo, sha, "passport/lane", "success" if v["lane"] == "GREEN" else "failure" if v["lane"] == "RED" else "success",
               f"{v['lane']}: read {rc['lines_to_read']}/{rc['lines_total']} lines", c["html_url"])
        status(repo, sha, "passport/owner-signature", "pending",
               f"Awaiting {p['requirement']['owner'].split(' — ')[0]} ({len(p['refusals'])} decisions open)", c["html_url"])
        print(f"{req}: PR #{pr['number']} {v['lane']} → {c['html_url']}")


def sign(repo, req, by, decision, risk, answers, full_read):
    p = passport(req)
    pr = find_pr(repo, p["change"]["branch"])
    sha = pr["head"]["sha"]
    if not sha.startswith(p["change"]["head"]):
        sys.exit(f"refused: PR head {sha[:8]} is not the commit the passport covers ({p['change']['head']})")
    owner = p["requirement"]["owner"].split(" — ")[0]
    if by != owner:
        sys.exit(f"refused: the passport names {owner!r} as owner, not {by!r}")
    if decision == "accept" and p["verdict"]["lane"] == "RED" and not full_read:
        sys.exit("refused: accepting a RED change requires --full-read")
    ans = dict(a.split("=", 1) for a in answers)
    missing = [r["id"] for r in p["refusals"] if r["id"] not in ans]
    if missing:
        sys.exit(f"refused: no answer for refusal(s) {', '.join(missing)} (use --answer R1=accept|reject|send-back)")
    att = {"passport": req, "fingerprint": p["fingerprint"], "commit": sha, "pr": pr["html_url"],
           "lane": p["verdict"]["lane"], "decision": decision, "full_read": full_read,
           "decisions": [{"refusal": r["id"], "question": r["question"], "answer": ans[r["id"]]} for r in p["refusals"]],
           "checked": p["attestation_draft"]["checked"], "not_checked": p["attestation_draft"]["not_checked"],
           "residual_risk": risk, "signed_by": by,
           "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    att["digest"] = hashlib.sha256(json.dumps(att, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    (OUT / "signatures").mkdir(exist_ok=True)
    f = OUT / "signatures" / f"{req}-{sha[:8]}.json"
    f.write_text(json.dumps(att, ensure_ascii=False, indent=1), encoding="utf-8")
    state, word = DECISIONS[decision]
    body = "\n".join([
        f"## ✍️ Owner attestation · {req} · **{word}**", "",
        f"Signed by **{by}** on commit `{sha[:12]}` (passport fingerprint `{p['fingerprint']}`, "
        f"attestation digest `{att['digest']}`).", "",
        "| Refusal | Question | Owner's answer |", "|---|---|---|",
        *[f"| {d['refusal']} | {cut(d['question'], 140)} | {d['answer']} |" for d in att["decisions"]], "",
        f"**Residual risk accepted:** {risk}", "",
        f"<details><summary>Signed record (JSON)</summary>\n\n```json\n{json.dumps(att, ensure_ascii=False, indent=1)}\n```\n</details>"])
    c = gh("api", f"repos/{repo}/issues/{pr['number']}/comments", "--input", "-", data={"body": body})
    status(repo, sha, "passport/owner-signature", state, f"{by}: {word} (digest {att['digest']})", c["html_url"])
    print(f"{req}: {word} by {by} on {sha[:8]} → {c['html_url']}\n  record: {f}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("publish"); a.add_argument("--repo", required=True); a.add_argument("reqs", nargs="+")
    s = sub.add_parser("sign"); s.add_argument("--repo", required=True); s.add_argument("req")
    s.add_argument("--by", required=True); s.add_argument("--decision", choices=list(DECISIONS), required=True)
    s.add_argument("--risk", required=True); s.add_argument("--answer", action="append", default=[])
    s.add_argument("--full-read", action="store_true")
    s.add_argument("--print", action="store_true")
    a.add_argument("--print", action="store_true", help="print the comment and stop")
    x = ap.parse_args()
    if x.cmd == "publish":
        if x.print:
            for r in x.reqs:
                print(comment_md(passport(r)))
            return
        publish(x.repo, x.reqs)
    else:
        sign(x.repo, x.req, x.by, x.decision, x.risk, x.answer, x.full_read)


if __name__ == "__main__":
    main()
