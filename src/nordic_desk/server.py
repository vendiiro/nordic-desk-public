"""Local server for the site: static pages from out/site plus a small JSON/HTML API for search.

Bound to 127.0.0.1 only: the pages hold real holdings and must not be reachable from the network.
Routes: /api/search?q=, /api/discover?list=, /api/card?t= (builds the card, stores it in out/cards.json,
re-renders cards.html and returns the card's HTML).
"""
from __future__ import annotations

import hmac
import json
import re
import secrets
import socket
import threading
from http.cookies import SimpleCookie
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .candidates import ALLOWED_EXCHANGES, ALLOWED_TYPES, search, yf_search

HOST, PORT = "127.0.0.1", 8765
DISCOVER = {
    "undervalued_large_caps": "Undervalued large companies",
    "undervalued_growth_stocks": "Undervalued growth stocks",
    "growth_technology_stocks": "Growth technology stocks",
    "portfolio_anchors": "Portfolio anchors",
    "top_etfs_us": "Top US ETFs",
    "technology_etfs": "Technology ETFs",
    "most_actives": "Most traded today",
}
TICKER = re.compile(r"^[A-Z0-9.^=-]{1,15}$")
_CARD_LOCK = threading.Lock()  # write_cards reads, changes and writes cards.json


def allowed(host: str, path: str, headers, port: int, lan: dict | None = None, query_key: str | None = None) -> bool:
    """Only this machine's own address (blocks DNS rebinding); API calls only from our own page script.
    In LAN mode the machine's LAN address is allowed too, but every request must carry the key (link or cookie)."""
    local = host in (f"127.0.0.1:{port}", f"localhost:{port}")
    if lan:
        cookie = SimpleCookie(headers.get("Cookie", "")).get("desk_key")
        given = query_key or (cookie.value if cookie else "")
        if host not in (f"127.0.0.1:{port}", f"localhost:{port}", f"{lan['host']}:{port}"):
            return False
        if not hmac.compare_digest(given.encode(), lan["key"].encode()):
            return False
    elif not local:
        return False
    return not path.startswith("/api/") or headers.get("X-Desk") == "1"


def lan_ip() -> str:
    """This machine's address on the local network (no packet is sent)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 9))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def yf_screen(name: str) -> dict:
    import yfinance as yf

    return yf.screen(name, count=25)


def build_card_html(ticker: str, out_dir: Path = Path("out")) -> str:
    from .cards import write_cards
    from .views.cards import card_html, cards_page

    doc = write_cards([ticker], "searched", out_dir=out_dir)
    site = out_dir / "site"
    site.mkdir(parents=True, exist_ok=True)
    fc_file = out_dir / "forecasts.json"
    fc = json.loads(fc_file.read_text(encoding="utf-8")) if fc_file.exists() else None  # keep realistic and expected columns
    plan_file = out_dir / "plan.json"
    plan = json.loads(plan_file.read_text(encoding="utf-8")) if plan_file.exists() else None
    (site / "cards.html").write_text(cards_page(doc, plan, fc), encoding="utf-8")
    if ticker not in doc["cards"]:
        raise ValueError(doc["errors"].get(ticker, "no data"))
    return card_html(doc["cards"][ticker], doc["meta"].get("default_amount"), fc)


class Api:
    def __init__(self, search_fetch=yf_search, screen_fetch=yf_screen, card_builder=build_card_html):
        self.search_fetch, self.screen_fetch, self.card_builder = search_fetch, screen_fetch, card_builder

    def handle(self, route: str, query: dict) -> tuple[int, str, str]:
        arg = lambda k: (query.get(k) or [""])[0].strip()
        js = lambda obj, code=200: (code, "application/json; charset=utf-8", json.dumps(obj, ensure_ascii=False))
        if route == "/api/search":
            if not arg("q"):
                return js({"error": "type a name or a ticker"}, 400)
            return js(search(arg("q"), fetch=self.search_fetch))
        if route == "/api/discover":
            name = arg("list")
            if name not in DISCOVER:
                return js({"error": "unknown list"}, 400)
            rows = [{"symbol": q["symbol"], "name": q.get("shortName") or q.get("longName") or q["symbol"],
                     "exchange": q.get("exchange"), "type": q.get("quoteType"), "rating": q.get("averageAnalystRating"),
                     "change": q.get("regularMarketChangePercent")}
                    for q in self.screen_fetch(name).get("quotes", [])
                    if q.get("exchange") in ALLOWED_EXCHANGES and q.get("quoteType") in ALLOWED_TYPES]
            return js(rows)
        if route == "/api/card":
            t = arg("t").upper()
            if not TICKER.match(t):
                return js({"error": "not a ticker"}, 400)
            try:
                with _CARD_LOCK:
                    html = self.card_builder(t)
                return 200, "text/html; charset=utf-8", html
            except Exception as e:
                return js({"error": f"{t}: {e}"}, 502)
        return js({"error": "not found"}, 404)


class Handler(SimpleHTTPRequestHandler):
    api = Api()
    lan: dict | None = None

    def end_headers(self):
        if getattr(self, "_set_key", False):
            self.send_header("Set-Cookie", f"desk_key={self.lan['key']}; HttpOnly; SameSite=Strict; Path=/")
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404, "Not found")
        return None

    def do_GET(self):
        u = urlparse(self.path)
        qk = (parse_qs(u.query).get("k") or [None])[0]
        if not allowed(self.headers.get("Host", ""), u.path, self.headers, self.server.server_address[1], self.lan, qk):
            self.send_error(403, "Forbidden")
            return
        self._set_key = bool(self.lan and qk)  # the key from the link becomes a cookie for the other pages
        if not u.path.startswith("/api/"):
            return super().do_GET()
        code, ctype, body = self.api.handle(u.path, parse_qs(u.query))
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class ExclusiveServer(ThreadingHTTPServer):
    allow_reuse_address = False  # on Windows reuse lets two servers share a port and steal requests


def make_server(site_dir: Path, port: int = PORT, tries: int = 10, lan: dict | None = None) -> ThreadingHTTPServer:
    """Bind to the first free port from `port` on, never sharing a port with another program."""
    handler = type("LanHandler", (Handler,), {"lan": lan}) if lan else Handler
    for p in range(port, port + tries):
        try:
            return ExclusiveServer(("0.0.0.0" if lan else HOST, p), partial(handler, directory=str(site_dir)))
        except OSError:
            continue
    raise OSError(f"no free port between {port} and {port + tries - 1}")


def serve(site_dir: Path = Path("out/site"), port: int = PORT, lan: bool = False) -> None:
    cfg = {"host": lan_ip(), "key": secrets.token_urlsafe(16)} if lan else None
    httpd = make_server(site_dir, port, lan=cfg)
    p = httpd.server_address[1]
    print(f"Serving http://{HOST}:{p}/cards.html  (Ctrl+C to stop)", flush=True)
    if cfg:
        print(f"Phone on the same Wi-Fi: http://{cfg['host']}:{p}/aamu.html?k={cfg['key']}", flush=True)
        print("The key changes on every start. Anyone with the link on your network can see the pages.", flush=True)
    httpd.serve_forever()
