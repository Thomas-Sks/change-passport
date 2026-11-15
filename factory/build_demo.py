#!/usr/bin/env python3
"""Build out/demo.html: the jury demo page, with every passport and measurement embedded.

  python3 build_demo.py                # then open out/demo.html (static, recorded replays)
  python3 server.py  -> http://127.0.0.1:8765/demo.html   (same page, live replays enabled)

Recorded replays are read from out/recorded/<REQ>-<ID>.json (see record_replays below);
they are the fallback when the page is opened without the server or a live replay fails.
"""
import argparse, json, sys
from pathlib import Path
import yaml

HERE = Path(__file__).parent
OUT = HERE / "out"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def collect():
    passports = {p.name.split(".")[0]: load(p) for p in sorted(OUT.glob("REQ-*.passport.json")) if ".live." not in p.name}
    replayable = []
    for f in sorted(HERE.glob("repro-REQ-*.yaml")):
        req = f.stem.replace("repro-", "")
        for eid, spec in (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("evidence", {}).items():
            replayable.append({"req": req, "id": eid, "title": spec.get("title", eid), "kind": spec.get("kind")})
    recorded = {p.stem: load(p) for p in sorted((OUT / "recorded").glob("*.json"))} if (OUT / "recorded").exists() else {}
    extra = {}
    for name in ("mutation-REQ-2297", "seeded-bugs-2297", "catching-REQ-2297"):
        if (OUT / f"{name}.json").exists():
            extra[name] = load(OUT / f"{name}.json")
    live = {p.parent.name: load(p) for p in sorted((OUT / "live").glob("*/status.json"))} if (OUT / "live").exists() else {}
    trust = yaml.safe_load((HERE / "trust.yaml").read_text(encoding="utf-8")).get("zones", {})
    return {"passports": passports, "replayable": replayable, "recorded": recorded, "extra": extra, "trust": trust, "live": live}


def record_replays(targets):
    """Run replays now and keep their results as the page's recorded fallback."""
    sys.path.insert(0, str(HERE))
    import replay
    (OUT / "recorded").mkdir(exist_ok=True)
    for t in targets:
        req, eid = t.split(":")
        print("replaying", req, eid, "...", flush=True)
        res = replay.replay(eid, None, req)
        (OUT / "recorded" / f"{req}-{eid}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", nargs="*", metavar="REQ:ID", help="e.g. REQ-2283:E1 REQ-2297:E3")
    a = ap.parse_args()
    if a.record:
        record_replays(a.record)
    data = json.dumps(collect(), ensure_ascii=False).replace("</", "<\\/")
    tpl = (HERE / "demo" / "demo.template.html").read_text(encoding="utf-8")
    out = OUT / "demo.html"
    out.write_text(tpl.replace("/*__DATA__*/null", data), encoding="utf-8")
    print(out, round(out.stat().st_size / 1024), "KB")
    flow = OUT / "flow.html"
    flow.write_text((HERE / "demo" / "flow.html").read_text(encoding="utf-8"), encoding="utf-8")
    print(flow, round(flow.stat().st_size / 1024), "KB")
    import shutil
    shutil.copytree(HERE / "demo" / "vendor", OUT / "vendor", dirs_exist_ok=True)


if __name__ == "__main__":
    main()
