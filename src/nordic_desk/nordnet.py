"""Read Nordnet files: the portfolio report PDF (holdings) and the daily-development export (record).

Neither file, nor the account number printed in them, is ever copied into the repository.
"""
from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

import pandas as pd

from .config import Holdings, Instrument, Position

# Thousands separators inside a Nordnet number are no-break or thin spaces; a plain space separates fields.
MINUS = chr(0x2212)
SEPARATORS = (chr(0x00A0), chr(0x202F), chr(0x2009))  # no-break, narrow no-break, thin space
NUM = rf"[+\-{MINUS}]?\d+(?:[{''.join(SEPARATORS)}]\d{{3}})*(?:,\d+)?"
ROW = re.compile(
    rf"^(?P<name>.*?)\s*(?P<price>{NUM}) (?P<cur>[A-Z]{{3}}) (?P<cost>{NUM}) (?P<qty>{NUM}) "
    rf"(?P<value>{NUM}) (?P<result>{NUM}) (?P<share>{NUM})%$"
)
CASH = re.compile(rf"^Likvidit varat (?P<value>{NUM}) (?P<share>{NUM})%$")
DATE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
ACCOUNT_LINE = re.compile(r"^\d{6,}\s+\d{2}\.\d{2}\.\d{4}$")


def parse_number(s: str) -> float:
    s = s.strip().rstrip("%").replace(MINUS, "-")
    for sep in (*SEPARATORS, " "):
        s = s.replace(sep, "")
    return float(s.replace(",", "."))


def parse_report_text(text: str, instruments: dict[str, Instrument]) -> Holdings:
    m = DATE.search(text)
    if not m:
        raise ValueError("no report date found")
    as_of = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    positions: list[Position] = []
    cash = 0.0
    pending: list[str] = []  # name lines wrapped above a row that starts with the price
    for line in (raw.strip() for raw in text.splitlines()):
        if not line or ACCOUNT_LINE.match(line):
            pending = []
            continue
        if c := CASH.match(line):
            cash = parse_number(c.group("value"))
            pending = []
            continue
        r = ROW.match(line)
        if not r:
            pending.append(line)
            continue
        tails = [" ".join(pending[-k:]) for k in (1, 2, 3) if len(pending) >= k]
        name = r.group("name") or next((n for n in tails if n in instruments), tails[min(1, len(tails) - 1)] if tails else "")
        pending = []
        value = parse_number(r.group("value"))
        inst = instruments.get(name)
        positions.append(Position(
            name=name, ticker=inst.ticker if inst else None, quantity=parse_number(r.group("qty")),
            value_eur=value, cost_eur=round(value - parse_number(r.group("result")), 2),
        ))
    return Holdings(as_of, positions, cash)


def parse_report(pdf_path: str | Path, instruments: dict[str, Instrument]) -> Holdings:
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages)
    return parse_report_text(text, instruments)


def _toml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_holdings(h: Holdings, path: str | Path = "config/holdings.local.toml") -> None:
    lines = ["# Written by `nordic-desk import-report`. Private: git-ignored, never commit.",
             f"as_of = {h.as_of.isoformat()}", f"cash_eur = {h.cash_eur!r}", ""]
    for p in h.positions:
        lines += ["[[position]]", f"name = {_toml_str(p.name)}"]
        if p.ticker:
            lines.append(f"ticker = {_toml_str(p.ticker)}")
        lines += [f"quantity = {p.quantity!r}", f"value_eur = {p.value_eur!r}"]
        if p.cost_eur is not None:
            lines.append(f"cost_eur = {p.cost_eur!r}")
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def read_export(path: str | Path) -> pd.DataFrame:
    """Nordnet daily-development export: UTF-16, tab-separated, comma decimals."""
    with open(path, encoding="utf-16", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t"))[1:]
    rows = [r for r in rows if r and r[0].strip()]
    return pd.DataFrame({
        "date": pd.to_datetime([r[0] for r in rows]),
        "value": [parse_number(r[1]) for r in rows],
        "deposits": [parse_number(r[6]) for r in rows],
    })


def twr(df: pd.DataFrame) -> pd.Series:
    """Time-weighted growth of 1: each period's deposit change is taken out of that period's gain."""
    df = df[df["value"].cummax() > 0]  # rows before the first deposit have no value to grow
    v, d = df["value"].to_numpy(), df["deposits"].to_numpy()
    out = [1.0]
    for i in range(1, len(v)):
        out.append(out[-1] * (v[i] - (d[i] - d[i - 1])) / v[i - 1])
    return pd.Series(out, index=df["date"])
