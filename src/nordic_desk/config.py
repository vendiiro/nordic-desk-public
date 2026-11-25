"""Watchlist, instrument map and holdings read from TOML files under config/."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Instrument:
    name: str
    ticker: str
    currency: str
    tech: bool
    note: str
    holdings_from: str = ""  # Yahoo ticker whose fund holdings stand in for this instrument


@dataclass(frozen=True)
class Position:
    name: str
    ticker: str | None
    quantity: float
    value_eur: float
    cost_eur: float | None


@dataclass(frozen=True)
class Holdings:
    as_of: date
    positions: list[Position]
    cash_eur: float


def _read(path: str | Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_watchlist(path: str | Path = "config/watchlist.toml") -> list[str]:
    return list(_read(path)["tickers"])


def load_ideas(path: str | Path = "config/ideas.toml") -> dict[str, list[str]]:
    """Idea groups: group name -> tickers. Empty when the file is missing."""
    return {g: list(t) for g, t in _read(path).items()} if Path(path).exists() else {}


def load_tech(path: str | Path = "config/watchlist.toml") -> list[str]:
    return list(_read(path).get("tech", []))


def load_instruments(path: str | Path = "config/instruments.toml") -> dict[str, Instrument]:
    return {
        name: Instrument(name, v["ticker"], v["currency"], bool(v.get("tech", False)), v.get("note", ""),
                         v.get("holdings_from", ""))
        for name, v in _read(path).items()
    }


def load_holdings(path: str | Path = "config/holdings.local.toml") -> Holdings:
    d = _read(path)
    positions = [
        Position(p["name"], p.get("ticker"), float(p["quantity"]), float(p["value_eur"]),
                 float(p["cost_eur"]) if "cost_eur" in p else None)
        for p in d.get("position", [])
    ]
    return Holdings(d["as_of"], positions, float(d.get("cash_eur", 0.0)))
