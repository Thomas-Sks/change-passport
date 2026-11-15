#!/usr/bin/env python3
"""Render a passport JSON into a self-contained HTML page (the owner's view)."""
import html, json, sys
from pathlib import Path
import yaml
def repro_ids(req):
    f = Path(__file__).parent / f"repro-{req}.yaml"
    return set(yaml.safe_load(f.read_text())["evidence"]) if f.exists() else set()

E = html.escape
LANE = {"RED": ("var(--red)", "Red"), "ORANGE": ("var(--orange)", "Orange"), "GREEN": ("var(--green)", "Green")}
ST = {"proven": "ok", "supported": "ok", "confirmed": "ok", "pass": "ok", "present": "bad", "fail-before": "ok",
      "contradicted": "bad", "regression": "bad", "fails": "neutral", "fail": "bad",
      "unproven": "warn", "not demonstrated": "warn", "weak": "warn", "observed": "warn"}


def badge(s):
    k = next((v for key, v in ST.items() if str(s).startswith(key)), "warn" if "weak" in str(s) or "underestimated" in str(s) else "neutral")
    if str(s).startswith("confirmed"): k = "ok"
    return f'<span class="b {k}">{E(str(s))}</span>'


def render(p):
    rc, v, req = p["reading_contract"], p["verdict"], p["requirement"]
    REPRO = repro_ids(req["id"])
    color, lane_name = LANE[v["lane"]]
    ev_by = {e["id"]: e for e in p["evidence"]}
    rows = lambda items: "".join(items)

    def tlist(c):
        ts = c.get("tests", [])
        if not ts:
            return '<span class="b warn">no linked test</span>'
        return "<br>".join(f'<code>{E(t["test"])}</code> {badge(t["branch"])}' + (f' <span class="b warn">{E(", ".join(t["issues"]))}</span>' if t.get("issues") else "") for t in ts)
    crit = rows(f'<tr><td>{E(c["id"])}</td><td>{E(c["text"])}</td><td>{badge(c["status"])}</td><td>{E(", ".join(c["evidence"]) or "—")}</td><td>{tlist(c)}</td></tr>' for c in p["acceptance_criteria"])
    claims = rows(f'<tr><td>{E(c["id"])}</td><td>{E(c["text"])}</td><td>{badge(c["status"])}</td><td>{E(", ".join(c["evidence"]) or "—")}</td></tr>' for c in p["claims"])
    def replay_cells(e):
        if e["id"] not in REPRO:
            return ""
        i = E(e["id"])
        return (f'<div><button class="rp" onclick="openReplay(\'{i}\')">▶ Replay base / branch</button></div>'
                f'<div id="rp-{i}" class="rpanel hidden"><div class="muted">Scenario (editable):</div><textarea id="sc-{i}" rows="10" class="code"></textarea>'
                f'<div class="row"><button class="primary" onclick="runReplay(\'{i}\')">Run</button><span id="st-{i}" class="muted"></span></div>'
                f'<div id="res-{i}" class="cmp"></div></div>')
    evid = rows(f'<tr><td>{E(e["id"])}</td><td>{E(e["what"])}<div class="muted">{E(e.get("detail",""))}</div>{replay_cells(e)}</td><td>{badge(e["result"])}</td><td>{E(e["by"])}</td></tr>' for e in p["evidence"])
    finds = rows(f'''<div class="card"><div class="row"><b>{E(f["id"])} · {E(f["title"])}</b>{badge(f["verification"])}</div>
        <div class="muted">{E(f["lens"])} · severity {E(f["severity"])} · stated confidence {f.get("confidence","—")} · {E(f["file"])}:{f.get("line","")}</div>
        <pre>{E(f["quote"])}</pre><div>Affects: {E(", ".join(f.get("affects",[])))} · Verification evidence: {E(", ".join(f["verification_evidence"]) or "none")}</div>
        {f'<div class="muted">{E(f["verification_note"])}</div>' if f.get("verification_note") else ""}
        <button class="flag" onclick="this.textContent='Flagged as incorrect ✓'">Incorrect?</button></div>''' for f in p["findings"])
    missed = rows(f'<li><b>{E(m["id"])}</b> — {E(m["what"])} <span class="muted">({E(", ".join(m["evidence"]))} ; {E(m.get("note",""))})</span></li>' for m in p["missed_by_ai"])
    refusal_rows = rows(f'''<tr><td>{E(r["id"])}</td><td>{E(r["question"])}<div class="muted">{E(r["why"])} · source: {E(r["source"])}</div></td>
        <td>{badge("major" if r["severity"]=="major" else "minor")}</td><td>{E(r["decider"])}</td>
        <td><select data-ref="{E(r["id"])}"><option value="">— to decide —</option><option>Accepted</option><option>Rejected: send back to the agent</option><option>Accepted with condition</option></select></td></tr>''' for r in p["refusals"])
    reads = rows(f'''<li><label><input type="checkbox" class="rd"> <code>{E(m["file"])}</code> <span class="muted">{E(m["header"])} · {m["lines"]} lines · {E(m["why"])}</span></label></li>''' for m in rc["must_read"])
    excl = rows(f'<tr><td>{E(x["what"])}</td><td>{x["lines"]}</td><td>{E(x["why"])}</td><td class="muted">{E(x["proof"])}</td></tr>' for x in rc.get("excluded", []))
    mflag = rows(f'<li><b>{E(m["id"])}</b> <code>{E(m["file"])}</code><pre>{E(chr(10).join(m["offending"]))}</pre></li>' for m in p["mechanical"]["flagged"])
    orph = rows(f'<li><code>{E(o["file"])}</code> <span class="muted">{E(o["header"])}</span><pre>{E(chr(10).join(o["preview"]))}</pre></li>' for o in p["traceability"]["orphans"])
    zones = rows(f'<tr><td>{E(z["zone"])}</td><td>{E(z["class"])}</td><td>{z["files"]}</td><td>{z["lines"]}</td><td>{E(z["trust"])}</td></tr>' for z in p["zones"])
    reasons = rows(f'<li class="red">{E(r)}</li>' for r in v["reasons_red"]) + rows(f'<li>{E(r)}</li>' for r in v["reasons_orange"])
    checked = rows(f'<tr><td>{E(c["what"])}</td><td>{E(c["by"])}</td></tr>' for c in p["attestation_draft"]["checked"])
    notchk = rows(f'<tr><td>{E(c["what"])}</td><td>{E(c["why"])}</td></tr>' for c in p["attestation_draft"]["not_checked"])
    ai_block = f'''<h2>4 · What the AI found (opinion + verification)</h2>{finds or '<p class="muted">No AI review for this change.</p>'}
      {f'<h3>What the AI missed (found by the executed evidence)</h3><ul>{missed}</ul>' if missed else ''}''' if True else ""

    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Passport {E(req["id"])}</title><style>
:root{{--bg:#fafaf9;--fg:#1c1917;--mut:#6b6560;--card:#fff;--line:#e7e5e4;--red:#c2410c;--orange:#b45309;--green:#15803d;--ok:#dcfce7;--okf:#166534;--bad:#fee2e2;--badf:#991b1b;--warn:#fef3c7;--warnf:#92400e;--code:#f5f5f4}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#161412;--fg:#ece9e6;--mut:#a8a29e;--card:#1f1c1a;--line:#34302c;--code:#2a2623;--ok:#14532d;--okf:#bbf7d0;--bad:#7f1d1d;--badf:#fecaca;--warn:#78350f;--warnf:#fde68a}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}} main{{max-width:1000px;margin:auto;padding:24px 16px 80px}}
h1{{font-size:22px;margin:0 0 4px}} h2{{font-size:17px;margin:32px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}} h3{{font-size:15px}}
.muted{{color:var(--mut);font-size:13px}} table{{width:100%;border-collapse:collapse;font-size:14px}} td,th{{text-align:left;padding:6px;border-bottom:1px solid var(--line);vertical-align:top}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;margin:8px 0}} .row{{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}}
pre{{background:var(--code);padding:8px;border-radius:6px;overflow-x:auto;font-size:12px;white-space:pre-wrap}} code{{font-size:12px;word-break:break-all}}
.b{{display:inline-block;padding:1px 8px;border-radius:99px;font-size:12px;white-space:nowrap}} .ok{{background:var(--ok);color:var(--okf)}} .bad{{background:var(--bad);color:var(--badf)}} .warn{{background:var(--warn);color:var(--warnf)}} .neutral{{background:var(--code)}}
.lane{{display:inline-block;padding:4px 14px;border-radius:6px;color:#fff;background:{color};font-weight:600}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:16px 0}} .kpi{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px}} .kpi b{{font-size:22px;display:block}}
li.red{{color:var(--red)}} .gate{{border:2px dashed var(--line);border-radius:8px;padding:12px}} .hidden{{display:none}}
button{{font:inherit;padding:6px 12px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}} button.primary{{background:var(--fg);color:var(--bg)}} .flag{{font-size:12px;margin-top:6px}}
.rp{{margin-top:6px;font-size:13px}} .rpanel{{margin-top:8px;border:1px solid var(--line);border-radius:8px;padding:10px;background:var(--bg)}}
textarea.code{{font:12px/1.4 ui-monospace,monospace}} .cmp{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:8px;margin-top:8px}}
.cmp .side{{border:1px solid var(--line);border-radius:6px;padding:8px;min-width:0}} .cmp pre{{max-height:260px;overflow:auto}} .verdict{{grid-column:1/-1;font-weight:600}}
textarea,input[type=text],select{{font:inherit;width:100%;box-sizing:border-box;padding:6px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}} select{{min-width:150px}}
</style></head><body><main>
<div class="muted">Change passport · fingerprint {E(p["fingerprint"])} · {E(p["change"]["branch"])} {E(p["change"]["base"])}..{E(p["change"]["head"])}</div>
<h1>{E(req["id"])} — {E(req["title"])}</h1>
<div class="row"><div>Named owner: <b>{E(req.get("owner") or "")}</b><br><span class="muted">Policy guardian: {E(req.get("policy_guardian") or "")} · <a href="{E(req.get("source") or "#")}">source requirement</a></span></div>
<div><span class="lane">{lane_name} lane</span></div></div>
<div class="card"><b>Action:</b> {E(v["action"])}</div>
<div class="kpis"><div class="kpi"><b>{rc["files_to_read"]} / {rc["files_total"]}</b>files to read</div><div class="kpi"><b>{rc["lines_to_read"]} / {rc["lines_total"]}</b>lines to read</div>
<div class="kpi"><b>{p["mechanical"]["passed"]}</b>files proven by rule</div><div class="kpi"><b>{len(p["refusals"])}</b>decisions refused by the AI</div><div class="kpi"><b>{len(p["findings"])}</b>verified AI findings</div></div>

<h2>1 · Before looking at the AI's opinion</h2>
<div class="gate" id="gate"><p>Answer first, in your own words (orange and red):</p>
<p>a) Do the acceptance criteria faithfully reflect the source requirement?</p><textarea id="q1" rows="2"></textarea>
<p>b) Which behaviour must absolutely stay unchanged for users?</p><textarea id="q2" rows="2"></textarea>
<p><button class="primary" onclick="openPassport()">Show the passport</button> <span class="muted" id="gmsg"></span></p></div>

<div id="body" class="hidden">
<h2>2 · Requirement: locked criteria and the agent's claims</h2>
<table><tr><th>Criterion</th><th>Text (locked)</th><th>Status</th><th>Evidence</th><th>Linked tests (result on the branch)</th></tr>{crit}</table>
<p class="muted">A criterion is “supported” only if at least one test that cites it (AC-n) passes on the branch, with no assertion weakness.</p>
<h3>The agent's claims</h3><table><tr><th>ID</th><th>Claim</th><th>Status</th><th>Evidence</th></tr>{claims}</table>

<h2>3 · Evidence (independent of the agent)</h2>
<table><tr><th>ID</th><th>What was checked</th><th>Result</th><th>By</th></tr>{evid}</table>
<p class="muted">Mechanical rule derived from the requirement: {p["mechanical"]["passed"]} files compliant · {len(p["mechanical"]["flagged"])} flagged.</p>
{f'<h3>Mechanical files outside the rule</h3><ul>{mflag}</ul>' if mflag else ''}
{f'<h3>Code not traced to any claim (orphan)</h3><ul>{orph}</ul>' if orph else ''}

{ai_block}

<h2>5 · What the AI refused to decide — for you to settle</h2>
<table><tr><th>ID</th><th>Question</th><th>Severity</th><th>Decider</th><th>Decision</th></tr>{refusal_rows}</table>

<h2>6 · Why this lane (deterministic verdict engine)</h2><ul>{reasons}</ul>
<details><summary>Partition by the policy</summary><table><tr><th>Zone</th><th>Class</th><th>Files</th><th>Lines</th><th>Trust</th></tr>{zones}</table></details>

<h2>7 · Reading contract — {rc["lines_to_read"]} lines out of {rc["lines_total"]}</h2>
<ul style="list-style:none;padding-left:0">{reads}</ul>
<p class="muted">Sorted by risk: orphan code and files outside the rule first, then weak tests, then sensitive zones.</p>
<h3>What does not need reading, and why</h3>
<table><tr><th>Excluded</th><th>Lines</th><th>Why</th><th>Proof</th></tr>{excl}</table>

<h2>8 · Attestation</h2>
<h3>Checked — by whom / what</h3><table>{checked}</table>
<h3>Not checked — why</h3><table>{notchk}</table>
<h3>Residual risk I accept</h3><textarea id="risk" rows="3" placeholder="Write the risk you accept, or “none: change sent back”"></textarea>
<p><input type="text" id="name" placeholder="Your name (named owner)"></p>
<button class="primary" onclick="sign()">Sign the passport</button> <span id="smsg" class="muted"></span>
<pre id="out" class="hidden"></pre>
</div></main>
<script>
const P={json.dumps({"id": req["id"], "fp": p["fingerprint"], "lane": v["lane"]})};
const REPLAYS=[];
const SERVED=location.protocol.startsWith('http');
async function openReplay(id){{const p=document.getElementById('rp-'+id);p.classList.toggle('hidden');const ta=document.getElementById('sc-'+id);
 if(!SERVED){{document.getElementById('st-'+id).textContent='Page opened as a file: run “python3 factory/server.py” then open http://127.0.0.1:8765/ — or “python3 factory/replay.py '+id+' --req '+P.id+'”.';return}}
 if(!ta.value){{try{{const r=await fetch('/scenario/'+P.id+'/'+id);const j=await r.json();ta.value=j.text||''}}catch(e){{ta.value=''}}}}}}
async function runReplay(id){{const st=document.getElementById('st-'+id),out=document.getElementById('res-'+id);st.textContent='Running in the sandbox on base and branch…';out.innerHTML='';
 try{{const r=await fetch('/replay/'+P.id+'/'+id,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{scenario:document.getElementById('sc-'+id).value}})}});const j=await r.json();
 if(j.error){{st.textContent=j.error;return}}
 REPLAYS.push({{evidence:id,verdict:j.verdict,scenario_modified:j.scenario_modified,at:j.replayed_at}});
 const esc=t=>t.replace(/[&<>]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]));
 const side=(n,s)=>`<div class="side"><b>${{n}}</b> — ${{esc(s.status)}} <span class="muted">(${{s.seconds}} s)</span><pre>${{esc(s.lines.join('\\n'))}}</pre></div>`;
 out.innerHTML=`<div class="verdict">${{esc(j.verdict)}}${{j.scenario_modified?' — scenario modified':''}}</div>`+side('Base '+j.base_ref,j.base)+side('Branch',j.branch);
 st.textContent='Replayed at '+j.replayed_at+' — recorded in the attestation.'}}catch(e){{st.textContent='Failed: local server unreachable.'}}}}
function openPassport(){{if(!q1.value.trim()||!q2.value.trim()){{gmsg.textContent='Answer both questions before seeing the AI\\'s opinion.';return}}gate.classList.add('hidden');body.classList.remove('hidden')}}
function sign(){{const d=[...document.querySelectorAll('select[data-ref]')].map(s=>({{refusal:s.dataset.ref,decision:s.value}}));
const unread=[...document.querySelectorAll('.rd')].filter(c=>!c.checked).length;
if(d.some(x=>!x.decision)){{smsg.textContent='Decide every refusal.';return}} if(unread){{smsg.textContent=unread+' reading-contract item(s) not ticked.';return}}
if(!risk.value.trim()||!name.value.trim()){{smsg.textContent='Residual risk and name required.';return}}
const a={{passport:P.id,fingerprint:P.fp,lane:P.lane,answers:{{criteria_reflect_requirement:q1.value,must_not_change:q2.value}},decisions:d,replays:REPLAYS,residual_risk:risk.value,signed_by:name.value,date:new Date().toISOString()}};
out.textContent=JSON.stringify(a,null,2);out.classList.remove('hidden');smsg.textContent='Attestation produced.'}}
</script></body></html>'''


if __name__ == "__main__":
    src = Path(sys.argv[1]); p = json.loads(src.read_text())
    dst = src.with_suffix("").with_suffix(".html"); dst.write_text(render(p)); print(dst)
