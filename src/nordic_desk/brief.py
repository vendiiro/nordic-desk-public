"""AI news brief per candidate: one Claude call turns the collected articles into sourced points and a tone count.

Only points that cite real article ids are kept. Briefs are cached per article set, and a monthly spend cap is checked
before each call. Held tickers are refused, so the holdings never leave this computer through this feature
(spec: docs/superpowers/specs/2026-11-20-idea-discovery-design.md, goal 2).
"""
from __future__ import annotations

import hashlib
import json
import tomllib
from datetime import date
from pathlib import Path

STORE = Path("data/news")


class BriefError(RuntimeError):
    pass


def load_cfg(path: str | Path = "config/news.toml") -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


_POINT = {"type": "object", "properties": {"text": {"type": "string"}, "sources": {"type": "array", "items": {"type": "integer"}}},
          "required": ["text", "sources"], "additionalProperties": False}
_EVENT = {**_POINT, "properties": {**_POINT["properties"], "date": {"type": "string"}}, "required": ["date", "text", "sources"]}
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["what", "for", "against", "events", "tone"], "properties": {
    "what": _POINT, "for": {"type": "array", "items": _POINT}, "against": {"type": "array", "items": _POINT},
    "events": {"type": "array", "items": _EVENT},
    "tone": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["id", "tone"], "properties": {
        "id": {"type": "integer"}, "tone": {"type": "string", "enum": ["positive", "neutral", "negative"]}}}}}}

SYSTEM = """You summarise recent news about one listed company for a long-term private investor.
Use only the numbered articles you are given; never add facts from memory.
Every point cites the ids of the articles it rests on in `sources`.
- what: what the company does, in at most two plain sentences.
- for / against: up to three points each that matter for owning the shares for years, one short sentence each.
- events: dated future events named in the articles (earnings dates, launches, votes), date as YYYY-MM-DD or YYYY-MM.
- tone: for each article, whether its news is positive, neutral or negative for this company.
Describe; do not advise. Never write buy, sell, hold or price targets of your own. If the articles say little, return fewer points."""


NO_KEY = "no Claude key: set ANTHROPIC_API_KEY (or run `ant auth login`) to write briefs"


def new_client():
    """A client with credentials, checked before any news is collected."""
    import anthropic

    c = anthropic.Anthropic()
    if not (c.api_key or c.auth_token or getattr(c, "credentials", None)):
        raise BriefError(NO_KEY)
    return c


def call_cost(usage, cfg: dict) -> float:
    """USD for every billed attempt: with a server-side fallback, `usage.iterations` lists each model that ran."""
    prices = cfg["prices"]
    top = max(prices.values(), key=lambda p: p[1])  # an unlisted model is priced at the dearest configured one
    rows = getattr(usage, "iterations", None) or [usage]
    return sum((r.input_tokens * p[0] + r.output_tokens * p[1]) / 1e6
               for r in rows for p in [prices.get(getattr(r, "model", None) or cfg["model"], top)])


def load_brief(ticker: str, store: Path = STORE) -> dict | None:
    f = Path(store) / "briefs" / f"{ticker.replace('^', '_')}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def clean_brief(raw: dict, articles: list[dict]) -> dict:
    ids = {a["id"] for a in articles}
    ok = lambda p: bool((p.get("text") or "").strip()) and bool(p.get("sources")) and set(p["sources"]) <= ids
    tidy = lambda p: {**{k: p[k] for k in p if k != "sources"}, "sources": sorted(set(p["sources"]))}
    pts = lambda key: [tidy(p) for p in raw.get(key) or [] if ok(p)][:3]
    tone = {"positive": 0, "neutral": 0, "negative": 0}
    for i, t in {t["id"]: t["tone"] for t in raw.get("tone") or [] if t.get("id") in ids}.items():
        tone[t] += 1
    w = raw.get("what") or {}
    return {"what": tidy(w) if ok(w) else None, "for": pts("for"), "against": pts("against"),
            "events": [tidy(e) for e in raw.get("events") or [] if ok(e) and (e.get("date") or "").strip()][:5],
            "tone": tone, "articles": [{k: a[k] for k in ("id", "url", "title", "date", "sites")} for a in articles]}


def _user(ticker: str, name: str, articles: list[dict]) -> str:
    body = "\n\n".join(f"[{a['id']}] {a['title']} ({', '.join(a['sites'])}, {a['date']})\n{a['text']}" for a in articles)
    return f"Company: {name} ({ticker}).\n\nArticles:\n\n{body}"


def make_brief(ticker: str, name: str, cfg: dict, held: set[str], store: Path = STORE, client=None, collect=None,
               today: str | None = None) -> dict:
    if ticker in held:
        raise BriefError(f"{ticker} is held: briefs are only for candidates, so your holdings never leave this computer")
    from . import news

    store, today = Path(store), today or date.today().isoformat()
    collect = collect or (lambda t, n, c: news.collect(t, n, c, cache_dir=store / "articles"))
    try:
        articles = collect(ticker, name, cfg)
    except news.SourceError as e:
        raise BriefError(str(e)) from e
    out = store / "briefs" / f"{ticker.replace('^', '_')}.json"
    key = hashlib.sha1((cfg["model"] + "".join(a["url"] for a in articles)).encode()).hexdigest()
    if out.exists():
        old = json.loads(out.read_text(encoding="utf-8"))
        if old.get("key") == key:
            return old  # same articles: no new call, no new cost
    meta = {"ticker": ticker, "name": name, "model": cfg["model"], "written": today, "key": key, "cost_usd": 0.0,
            "range": [min(a["date"] for a in articles), max(a["date"] for a in articles)] if articles else None}
    if articles:
        spend_f, month = store / "spend.json", today[:7]
        spend = json.loads(spend_f.read_text(encoding="utf-8")) if spend_f.exists() else {}
        cap = float(cfg["monthly_cap_usd"])
        if spend.get(month, 0.0) >= cap:
            raise BriefError(f"monthly AI budget reached (${spend[month]:.2f} of ${cap:.2f}); raise monthly_cap_usd in config/news.toml or wait for next month")
        r = _call(client, cfg, _user(ticker, name, articles))
        cost = call_cost(r.usage, cfg)
        spend[month] = round(spend.get(month, 0.0) + cost, 6)  # recorded before parsing: a refused call is billed too
        spend_f.parent.mkdir(parents=True, exist_ok=True)
        spend_f.write_text(json.dumps(spend), encoding="utf-8")
        raw = _parse(r)
        brief = {**meta, **clean_brief(raw, articles), "cost_usd": round(cost, 4)}
    else:
        brief = {**meta, **clean_brief({}, [])}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    return brief


def _call(client, cfg: dict, user: str):
    import anthropic

    try:
        client = client or anthropic.Anthropic()
        r = client.beta.messages.create(
            model=cfg["model"], max_tokens=16000, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            output_config={"effort": cfg["effort"], "format": {"type": "json_schema", "schema": SCHEMA}},
            system=SYSTEM, messages=[{"role": "user", "content": user}])
    except (anthropic.AuthenticationError, TypeError) as e:  # TypeError: the SDK found no key, token or profile at all
        raise BriefError(NO_KEY) from e
    except anthropic.APIError as e:
        raise BriefError(f"Claude request failed: {e}") from e
    return r


def _parse(r) -> dict:
    if r.stop_reason == "refusal":
        raise BriefError("Claude declined to write this brief")
    if r.stop_reason == "max_tokens":
        raise BriefError("the brief was cut off at the token limit")
    try:
        return json.loads(next(b.text for b in r.content if b.type == "text"))
    except (StopIteration, ValueError) as e:
        raise BriefError("Claude returned no readable brief") from e
