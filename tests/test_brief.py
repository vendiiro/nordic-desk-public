import json
from types import SimpleNamespace

import pytest

from nordic_desk.brief import BriefError, clean_brief, make_brief

ARTS = [{"id": i, "url": f"https://s{i}.example/a", "title": f"Story {i}", "date": f"2026-11-{10 + i}", "sites": [f"s{i}.example"],
         "text": "Invented text."} for i in (1, 2, 3)]
CFG = {"model": "claude-opus-5-5", "effort": "low", "monthly_cap_usd": 5.0,
       "prices": {"claude-opus-5-5": [4.0, 20.0], "claude-opus-5": [5.0, 25.0]},
       "days": 30, "max_articles": 20, "min_chars": 10, "paywall": []}

RAW = {"what": {"text": "Makes cooling units.", "sources": [1]},
       "for": [{"text": "Backlog grew.", "sources": [1, 2]}, {"text": "Made up claim.", "sources": []},
               {"text": "Unknown source.", "sources": [9]}, {"text": "New plant.", "sources": [3]},
               {"text": "Margins up.", "sources": [2]}, {"text": "Fourth valid.", "sources": [1]}],
       "against": [{"text": "Few customers.", "sources": [3]}],
       "events": [{"date": "2026-12-04", "text": "Results", "sources": [2]}, {"date": "", "text": "Someday", "sources": [1]}],
       "tone": [{"id": 1, "tone": "positive"}, {"id": 2, "tone": "negative"}, {"id": 3, "tone": "neutral"}, {"id": 7, "tone": "positive"}]}


def test_clean_brief_keeps_only_sourced_points():
    b = clean_brief(RAW, ARTS)
    assert [p["text"] for p in b["for"]] == ["Backlog grew.", "New plant.", "Margins up."]  # unsourced, unknown id dropped; max 3
    assert b["against"][0]["sources"] == [3] and b["what"]["text"] == "Makes cooling units."
    assert b["events"] == [{"date": "2026-12-04", "text": "Results", "sources": [2]}]
    assert b["tone"] == {"positive": 1, "neutral": 1, "negative": 1}
    assert [a["id"] for a in b["articles"]] == [1, 2, 3] and "text" not in b["articles"][0]


class FakeClient:
    def __init__(self, raw=RAW, stop="end_turn", iterations=None, error=None):
        self.calls, self.raw, self.stop, self.iterations, self.error = [], raw, stop, iterations, error
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        if self.error:
            raise self.error
        return SimpleNamespace(stop_reason=self.stop, content=[SimpleNamespace(type="text", text=json.dumps(self.raw))],
                               usage=SimpleNamespace(input_tokens=10_000, output_tokens=1_000, iterations=self.iterations))


def run(tmp_path, client, arts=ARTS, held=(), cfg=CFG):
    return make_brief("NRDL", "Nordlys Systems", cfg, held=set(held), store=tmp_path, client=client,
                      collect=lambda t, n, c: arts, today="2026-11-20")


def test_make_brief_saves_and_counts_spend(tmp_path):
    c = FakeClient()
    b = run(tmp_path, c)
    assert b["ticker"] == "NRDL" and b["model"] == "claude-opus-5-5" and b["cost_usd"] == pytest.approx(0.06)
    assert json.loads((tmp_path / "briefs" / "NRDL.json").read_text(encoding="utf-8"))["for"]
    assert json.loads((tmp_path / "spend.json").read_text(encoding="utf-8")) == {"2026-11": pytest.approx(0.06)}
    kw = c.calls[0]
    assert kw["model"] == "claude-opus-5-5" and kw["output_config"]["effort"] == "low"
    assert kw["output_config"]["format"]["type"] == "json_schema"
    sent = json.dumps(kw["messages"]) + kw["system"]
    assert "Story 1" in sent and "Nordlys Systems" in sent


def test_same_articles_no_second_call(tmp_path):
    c = FakeClient()
    run(tmp_path, c)
    run(tmp_path, c)
    assert len(c.calls) == 1


def test_cap_blocks_call(tmp_path):
    (tmp_path / "spend.json").write_text(json.dumps({"2026-11": 5.0}), encoding="utf-8")
    c = FakeClient()
    with pytest.raises(BriefError, match="budget"):
        run(tmp_path, c)
    assert c.calls == []


def test_held_ticker_refused(tmp_path):
    c = FakeClient()
    with pytest.raises(BriefError, match="held"):
        run(tmp_path, c, held={"NRDL"})
    assert c.calls == []


def test_no_articles_no_call(tmp_path):
    c = FakeClient()
    b = run(tmp_path, c, arts=[])
    assert c.calls == [] and b["articles"] == [] and b["for"] == []


def test_refusal_is_an_error_and_not_saved(tmp_path):
    with pytest.raises(BriefError, match="declined"):
        run(tmp_path, FakeClient(stop="refusal"))
    assert not (tmp_path / "briefs" / "NRDL.json").exists()
    assert json.loads((tmp_path / "spend.json").read_text(encoding="utf-8")) == {"2026-11": pytest.approx(0.06)}  # a refusal is still billed


def test_fallback_attempts_all_priced(tmp_path):
    its = [SimpleNamespace(type="message", model="claude-opus-5-5", input_tokens=10_000, output_tokens=500),
           SimpleNamespace(type="fallback_message", model="claude-opus-5", input_tokens=10_000, output_tokens=1_000)]
    b = run(tmp_path, FakeClient(iterations=its))
    assert b["cost_usd"] == pytest.approx(0.04 + 0.01 + 0.05 + 0.025)


def test_unknown_model_priced_at_highest():
    from nordic_desk.brief import call_cost
    u = SimpleNamespace(input_tokens=1_000_000, output_tokens=0, iterations=[SimpleNamespace(model="claude-new", input_tokens=1_000_000, output_tokens=0)])
    assert call_cost(u, CFG) == pytest.approx(5.0)


def test_missing_credentials_is_a_clear_error(tmp_path):
    with pytest.raises(BriefError, match="no Claude key"):
        run(tmp_path, FakeClient(error=TypeError("Could not resolve authentication method")))


def test_source_failure_keeps_old_brief(tmp_path):
    from nordic_desk.news import SourceError
    c = FakeClient()
    run(tmp_path, c)

    def down(t, n, cfg):
        raise SourceError("GDELT unavailable")
    with pytest.raises(BriefError, match="GDELT"):
        make_brief("NRDL", "Nordlys Systems", CFG, held=set(), store=tmp_path, client=c, collect=down, today="2026-11-20")
    assert json.loads((tmp_path / "briefs" / "NRDL.json").read_text(encoding="utf-8"))["for"] and len(c.calls) == 1


def test_new_client_without_credentials(monkeypatch):
    import anthropic
    from nordic_desk.brief import new_client
    monkeypatch.setattr(anthropic, "Anthropic", lambda: SimpleNamespace(api_key=None, auth_token=None, credentials=None))
    with pytest.raises(BriefError, match="no Claude key"):
        new_client()
    monkeypatch.setattr(anthropic, "Anthropic", lambda: SimpleNamespace(api_key="set", auth_token=None))
    assert new_client().api_key == "set"
