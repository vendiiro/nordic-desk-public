"""Write every view into out/site/ (git-ignored: the pages hold real holdings)."""
from __future__ import annotations

import json
from pathlib import Path

from .aamu import aamu_page
from .huurre import COMPARE_REDIRECT, desk_page
from .impact import impact_page
from .today import today_page


def _last_close(price_root: Path | None) -> str | None:
    """Newest stored SPY close: the analysis pages use the price store even when desk.json is older (a Nordnet record)."""
    from .. import prices
    spy = prices.load("SPY", price_root or prices.ROOT)
    return None if spy.empty else spy.index[-1].strftime("%Y-%m-%d")


def write_site(out_dir: Path = Path("out"), holdings_path: str = "config/holdings.local.toml", price_root: Path | None = None,
               ohlc_root: Path | None = None, fund_root: Path | None = None, hist_path: Path | None = None) -> list[Path]:
    import tomllib

    from ..analysis import subjects
    from ..forecasts import write_forecasts
    from .forecasts import forecasts_page
    out_dir = Path(out_dir)
    desk = json.loads((out_dir / "desk.json").read_text(encoding="utf-8"))
    aamu = json.loads((out_dir / "aamu.json").read_text(encoding="utf-8"))
    site = out_dir / "site"
    site.mkdir(parents=True, exist_ok=True)
    alerts = json.loads((out_dir / "alerts.json").read_text(encoding="utf-8")) if (out_dir / "alerts.json").exists() else []
    pages = {"impact.html": impact_page(desk), "compare.html": COMPARE_REDIRECT, "aamu.html": aamu_page(aamu, desk, alerts)}
    cards = out_dir / "cards.json"
    cards_doc = json.loads(cards.read_text(encoding="utf-8")) if cards.exists() else None
    subs = subjects(holdings_path, "config/instruments.toml", [r["ticker"] for r in desk["watchlist"]], cards_doc)
    fc = write_forecasts(out_dir, subs, desk, cards_doc, price_root, ohlc_root, fund_root, hist_path)
    target = Path("config/target.toml")
    card_default = tomllib.loads(target.read_text(encoding="utf-8")).get("card_default", 2000) if target.exists() else 2000
    pages["forecasts.html"] = forecasts_page(fc, card_default)
    if cards.exists():
        from .cards import cards_page
        plan = out_dir / "plan.json"
        pages["cards.html"] = cards_page(json.loads(cards.read_text(encoding="utf-8")),
                                         json.loads(plan.read_text(encoding="utf-8")) if plan.exists() else None, fc)
    from ..analysis import write_analysis
    analysed = write_analysis(out_dir, [r["ticker"] for r in desk["watchlist"]], holdings_path,
                              price_root=price_root, ohlc_root=ohlc_root, fund_root=fund_root, forecasts=fc, close=_last_close(price_root))
    verdicts = json.loads((out_dir / "analysis_index.json").read_text(encoding="utf-8"))["rows"]
    pages["desk.html"] = desk_page(desk, verdicts)
    from .goal import goal_page
    goal = json.loads((out_dir / "goal.json").read_text(encoding="utf-8")) if (out_dir / "goal.json").exists() else None
    pages["goal.html"] = goal_page(goal or {"available": False, "why": "No range yet: run nordic-desk build, then site."}, desk["meta"])
    pages["index.html"] = today_page(desk, aamu, alerts, verdicts, goal)
    written = []
    for name, html in pages.items():
        (site / name).write_text(html, encoding="utf-8")
        written.append(site / name)
    return written + analysed
