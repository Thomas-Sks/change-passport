#!/usr/bin/env python3
"""Local passport server (127.0.0.1 only): serves the passport pages and runs one-click replays.

  python3 server.py            # then open http://127.0.0.1:8765/REQ-2297.html

GET  /<page>.html          passport page (from out/)
GET  /scenario/<ID>        archived scenario of an evidence
POST /replay/<ID>          body {"scenario": "..."} optional -> side-by-side result; logged in out/replays.jsonl
"""
import json, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).parent))
import replay
import pipeline

HERE = Path(__file__).parent
OUT = HERE / "out"
LOCK = threading.Lock()  # one replay or pipeline at a time: worktrees are shared
RUNNING = {}  # live pipeline threads per requirement


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)

    def start_pipeline(self):
        req = self.path.strip("/").split("/")[1]
        if not (HERE / f"repro-{req}.yaml").exists():
            return self._send(404, '{"error":"no replayable proofs for this requirement"}')
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 2) or b"{}")
        if req in RUNNING and RUNNING[req].is_alive():
            return self._send(409, '{"error":"already running"}')
        def job():
            with LOCK:
                pipeline.run_pipeline(req, skip_review=bool(body.get("skip_review")))
        st = HERE / "out" / "live" / req / "status.json"
        st.unlink(missing_ok=True)
        RUNNING[req] = threading.Thread(target=job, daemon=True); RUNNING[req].start()
        return self._send(202, '{"started":true}')

    def do_GET(self):
        path = self.path.split("?")[0]
        if path.startswith("/pipeline/"):
            st = HERE / "out" / "live" / path.strip("/").split("/")[1] / "status.json"
            return self._send(200, st.read_bytes()) if st.exists() else self._send(200, '{"steps":[],"done":false,"pending":true}')
        if path.startswith("/scenario/"):
            parts = path.strip("/").split("/")
            req, eid = (parts[1], parts[2]) if len(parts) == 3 else ("REQ-2297", parts[-1])
            f_ = HERE / f"repro-{req}.yaml"
            spec = yaml.safe_load(f_.read_text())["evidence"].get(eid) if f_.exists() else None
            if not spec:
                return self._send(404, '{"error":"evidence has no replayable scenario"}')
            return self._send(200, json.dumps({"file": spec["scenario"]["file"], "text": (HERE / spec["scenario"]["file"]).read_text()}))
        name = path.strip("/") or "demo.html"
        f = (OUT / name).resolve()
        if f.parent not in (OUT.resolve(), (OUT / "vendor").resolve()) or not f.exists():
            return self._send(404, "not found", "text/plain; charset=utf-8")
        ctype = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8"}.get(f.suffix, "application/json; charset=utf-8")
        return self._send(200, f.read_bytes(), ctype)

    def do_POST(self):
        if self.path.startswith("/pipeline/"):
            return self.start_pipeline()
        if not self.path.startswith("/replay/"):
            return self._send(404, "{}")
        parts = self.path.strip("/").split("/")
        req, eid = (parts[1], parts[2]) if len(parts) == 3 else ("REQ-2297", parts[-1])
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 2) or b"{}")
        tmp = None
        if body.get("scenario"):
            tmp = OUT / f".scenario-{eid}.tmp"; tmp.write_text(body["scenario"], encoding="utf-8")
        try:
            with LOCK:
                res = replay.replay(eid, str(tmp) if tmp else None, req)
        except (KeyError, FileNotFoundError):
            return self._send(404, '{"error":"evidence has no replayable scenario"}')
        except Exception as ex:  # never answer with an empty reply: say what failed
            import traceback; traceback.print_exc()
            return self._send(500, json.dumps({"error": f"{type(ex).__name__}: {ex}"}))
        finally:
            if tmp: tmp.unlink(missing_ok=True)
        with open(OUT / "replays.jsonl", "a", encoding="utf-8") as log:
            log.write(json.dumps({"requirement": req, **{k: res[k] for k in ("evidence", "verdict", "scenario_modified", "replayed_at")}}, ensure_ascii=False) + "\n")
        return self._send(200, json.dumps(res, ensure_ascii=False))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"Demo: http://127.0.0.1:{port}/demo.html")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
