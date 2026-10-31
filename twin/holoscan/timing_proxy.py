"""A timing proxy between the game and a gate brain: where does a reading's age come from?

    python twin/holoscan/timing_proxy.py --listen 8773 --brain http://127.0.0.1:8774 --log FILE

Step 2 of "Next" in docs/HOLOSCAN_GATE.md. The game posts to the proxy as it would to the brain;
the proxy forwards each request unchanged and writes one line per request:

- `age_at_arrival_s`: for each attested reading in the body, the proxy's clock minus its signed_at,
  when the request reached the proxy (oldest and newest). This is the age the game's side gave it:
  measurement to sending, and the request's time on the wire.
- `brain_s`: from forwarding to the brain's answer. This holds the time the request waited for the
  brain (its locks, other requests) and the brain's own work.
- `stale_in_answer`: how many times the brain's answer says "stale".

The brain is not changed. The proxy adds a forward on the loopback, well under a millisecond.
"""

from __future__ import annotations

import argparse
import http.client
import json
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


def reading_ages(body: bytes, now: float) -> list[float]:
    try:
        req = json.loads(body)
    except Exception:
        return []
    ages = []
    for r in req.get("sensors", []) if isinstance(req, dict) else []:
        at = (r.get("attestation") or {}).get("signed_at") if isinstance(r, dict) else None
        if at:
            try:
                ages.append(now - datetime.fromisoformat(at).timestamp())
            except ValueError:
                pass
    return ages


def make_handler(brain: str, log_path: str, lock: threading.Lock):
    u = urlparse(brain)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _forward(self, method: str):
            t_arrive = time.time()
            n = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(n) if n > 0 else b""
            ages = reading_ages(body, t_arrive) if method == "POST" else []
            headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection")}
            t_fwd = time.time()
            try:
                c = http.client.HTTPConnection(u.hostname, u.port, timeout=600)
                c.request(method, self.path, body=body or None, headers=headers)
                r = c.getresponse()
                data, status, rh = r.read(), r.status, r.getheaders()
                c.close()
            except Exception as e:
                data, status, rh = json.dumps({"error": f"proxy: {type(e).__name__}"}).encode(), 502, []
            t_back = time.time()
            self.send_response(status)
            for k, v in rh:
                if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            row = {"t": t_arrive, "method": method, "path": self.path, "status": status, "bytes_in": n,
                   "readings": len(ages), "age_at_arrival_s": [min(ages), max(ages)] if ages else None,
                   "brain_s": t_back - t_fwd, "stale_in_answer": data.count(b"stale")}
            with lock, open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")

        def do_GET(self):
            self._forward("GET")

        def do_POST(self):
            self._forward("POST")

    return Handler


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", type=int, required=True)
    ap.add_argument("--brain", required=True)
    ap.add_argument("--log", required=True)
    a = ap.parse_args(argv)
    srv = ThreadingHTTPServer(("127.0.0.1", a.listen), make_handler(a.brain, a.log, threading.Lock()))
    print(f"timing proxy on 127.0.0.1:{a.listen} -> {a.brain}, log {a.log}", flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
