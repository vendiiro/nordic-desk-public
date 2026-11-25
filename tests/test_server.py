import json

from nordic_desk import server

HITS = [{"symbol": "NOK", "shortname": "Nokia", "exchange": "NYQ", "quoteType": "EQUITY"},
        {"symbol": "X.HA", "shortname": "x", "exchange": "HAN", "quoteType": "EQUITY"}]
SCREEN = {"quotes": [{"symbol": "NU", "exchange": "NYQ", "quoteType": "EQUITY", "shortName": "Nu Holdings", "averageAnalystRating": "1.6 - Buy",
                      "regularMarketChangePercent": 1.5},
                     {"symbol": "ZZ.L", "exchange": "LSE", "quoteType": "EQUITY", "shortName": "Elsewhere"}]}


def app():
    return server.Api(search_fetch=lambda q: HITS, screen_fetch=lambda name: SCREEN,
                      card_builder=lambda t: f'<article class="card" id="{t}">card {t}</article>')


def test_search_returns_allowed_hits():
    status, ctype, body = app().handle("/api/search", {"q": ["nokia"]})
    assert status == 200 and ctype.startswith("application/json")
    assert [h["symbol"] for h in json.loads(body)] == ["NOK"]


def test_empty_query_is_bad_request():
    assert app().handle("/api/search", {"q": [" "]})[0] == 400


def test_discover_lists_and_filters():
    status, _, body = app().handle("/api/discover", {"list": ["undervalued_large_caps"]})
    rows = json.loads(body)
    assert status == 200 and [r["symbol"] for r in rows] == ["NU"] and rows[0]["rating"] == "1.6 - Buy"


def test_discover_unknown_list_rejected():
    assert app().handle("/api/discover", {"list": ["../etc"]})[0] == 400


def test_card_returns_html():
    status, ctype, body = app().handle("/api/card", {"t": ["nok"]})
    assert status == 200 and ctype.startswith("text/html") and 'id="NOK"' in body


def test_bad_ticker_rejected():
    assert app().handle("/api/card", {"t": ["<script>"]})[0] == 400


def test_unknown_route():
    assert app().handle("/api/nope", {})[0] == 404


def test_binds_to_localhost_only():
    assert server.HOST == "127.0.0.1"


def test_busy_port_moves_to_next(tmp_path):
    import socket
    blocker = socket.socket()
    blocker.bind((server.HOST, 0))
    blocker.listen()
    busy = blocker.getsockname()[1]
    try:
        httpd = server.make_server(tmp_path, busy)
        try:
            assert httpd.server_address[1] != busy
        finally:
            httpd.server_close()
    finally:
        blocker.close()


def test_request_guard():
    ok = {"Host": "127.0.0.1:8766", "X-Desk": "1"}
    assert server.allowed("127.0.0.1:8766", "/api/card", ok, 8766)
    assert server.allowed("localhost:8766", "/cards.html", {}, 8766)
    assert not server.allowed("evil.example:8766", "/holdings.html", {}, 8766)       # DNS rebinding
    assert not server.allowed("127.0.0.1:8766", "/api/card", {}, 8766)               # cross-site GET without header


def test_card_builds_do_not_overlap():
    import threading
    import time
    state = {"now": 0, "max": 0}

    def slow(t):
        state["now"] += 1
        state["max"] = max(state["max"], state["now"])
        time.sleep(0.05)
        state["now"] -= 1
        return f'<article class="card" id="{t}"></article>'
    api = server.Api(card_builder=slow)
    ts = [threading.Thread(target=api.handle, args=("/api/card", {"t": [t]})) for t in ("AA", "BB", "CC")]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert state["max"] == 1


def test_no_directory_listing():
    from http.server import SimpleHTTPRequestHandler
    assert server.Handler.list_directory is not SimpleHTTPRequestHandler.list_directory


def test_lan_mode_needs_the_key():
    lan = {"host": "192.168.1.20", "key": "secret123"}
    h = "192.168.1.20:8766"
    assert not server.allowed(h, "/aamu.html", {}, 8766)                                  # LAN host refused without LAN mode
    assert not server.allowed(h, "/aamu.html", {}, 8766, lan=lan)                         # no key
    assert server.allowed(h, "/aamu.html", {}, 8766, lan=lan, query_key="secret123")      # key in the link
    assert server.allowed(h, "/desk.html", {"Cookie": "desk_key=secret123"}, 8766, lan=lan)
    assert not server.allowed(h, "/desk.html", {"Cookie": "desk_key=wrong"}, 8766, lan=lan)
    assert not server.allowed("evil.example:8766", "/aamu.html", {}, 8766, lan=lan, query_key="secret123")
    assert not server.allowed(h, "/api/card", {"Cookie": "desk_key=secret123"}, 8766, lan=lan)   # API still needs X-Desk


def test_lan_ip_is_an_address():
    ip = server.lan_ip()
    assert ip.count(".") == 3


def test_card_search_keeps_the_plan(tmp_path, monkeypatch):
    import json
    import nordic_desk.cards as C
    import nordic_desk.views.cards as V
    from nordic_desk.server import build_card_html
    (tmp_path / "plan.json").write_text(json.dumps({"amount": 2000}), encoding="utf-8")
    seen = {}
    monkeypatch.setattr(C, "write_cards", lambda t, g, out_dir: {"cards": {"X": {}}, "errors": {}, "meta": {}})
    monkeypatch.setattr(V, "cards_page", lambda doc, plan, fc: seen.setdefault("plan", plan) and "page")
    monkeypatch.setattr(V, "card_html", lambda *a: "card")
    assert build_card_html("X", tmp_path) == "card"
    assert seen["plan"] == {"amount": 2000}
