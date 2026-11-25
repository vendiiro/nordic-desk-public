import re
from datetime import date
from pathlib import Path

import pytest

from nordic_desk.config import load_holdings, load_instruments
from nordic_desk.nordnet import parse_number, parse_report_text, read_export, twr, write_holdings

TEXT = Path("tests/fixtures/report_page.txt").read_text(encoding="utf-8")


def test_parse_number():
    assert parse_number("\u2212152,47") == -152.47
    assert parse_number("-152,47") == -152.47
    assert parse_number("10\u00a0345,67") == 10345.67
    assert parse_number("10 345,67") == 10345.67
    assert parse_number("+1\u202f234,56") == 1234.56
    assert parse_number("31,25%") == 31.25


def test_report_lines_parsed():
    h = parse_report_text(TEXT, load_instruments())
    assert h.as_of == date(2026, 1, 15)
    assert h.cash_eur == 180.0
    names = [p.name for p in h.positions]
    assert names == ["Microsoft", "iShares Blockchain Technology UCITS ETF USD (Acc)", "Some Unknown Fund EUR", "Nordnet Suomi Indeksi"]
    ms = h.positions[0]
    assert (ms.ticker, ms.quantity, ms.value_eur) == ("MSFT", 4.0, 1800.0)
    assert ms.cost_eur == pytest.approx(1800.0 - 210.5)
    bc = h.positions[1]
    assert (bc.ticker, bc.value_eur, bc.cost_eur) == ("CBUT.DE", 200.0, 240.0)
    assert h.positions[3].quantity == 6.5


def test_unmapped_kept():
    h = parse_report_text(TEXT, load_instruments())
    unknown = h.positions[2]
    assert unknown.ticker is None and unknown.value_eur == 110.0


def test_written_holdings_round_trip_without_account_number(tmp_path):
    h = parse_report_text(TEXT, load_instruments())
    out = tmp_path / "holdings.local.toml"
    write_holdings(h, out)
    assert not re.search(r"\d{8}", out.read_text(encoding="utf-8"))
    back = load_holdings(out)
    assert back == h


def export_file(tmp_path, rows):
    head = "P\u00e4iv\u00e4m\u00e4\u00e4r\u00e4\tArvo yhteens\u00e4 (EUR)\tP\u00e4iv\u00e4kohtainen kehitys (%)\tKertynyt tuotto (%)\tP\u00e4iv\u00e4kohtainen kehitys (EUR)\tKertynyt tuotto (EUR)\tNettotalletukset (EUR)"
    lines = [head] + [f"{d}\t{v}\t0,00%\t0,00%\t0,00\t0,00\t{dep}" for d, v, dep in rows]
    p = tmp_path / "export.csv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-16")
    return p


def test_export_utf16_read(tmp_path):
    df = read_export(export_file(tmp_path, [("2025-01-03", "1000,00", "1000,00"), ("2025-01-10", "1\u00a0100,00", "1000,00")]))
    assert list(df.columns) == ["date", "value", "deposits"]
    assert df["value"].tolist() == [1000.0, 1100.0]
    assert str(df["date"].iloc[0].date()) == "2025-01-03"


def test_twr_ignores_deposits(tmp_path):
    df = read_export(export_file(tmp_path, [
        ("2025-01-03", "1000,00", "1000,00"),
        ("2025-01-10", "1500,00", "1500,00"),   # deposit of 500, no price change
        ("2025-01-17", "1650,00", "1500,00"),   # +10 %
    ]))
    t = twr(df)
    assert t.tolist() == pytest.approx([1.0, 1.0, 1.1])


def test_thin_space_thousands():
    assert parse_number("10\u2009345,67") == 10345.67
    h = parse_report_text("Raportti 15.01.2026\nMicrosoft 400,00 USD 350,00 4 1\u2009800,00 +210,50 40,00%\n", load_instruments())
    assert h.positions[0].value_eur == 1800.0


def test_twr_skips_leading_zero_rows(tmp_path):
    df = read_export(export_file(tmp_path, [
        ("2025-01-03", "0,00", "0,00"),
        ("2025-01-10", "1000,00", "1000,00"),
        ("2025-01-17", "1100,00", "1000,00"),
    ]))
    t = twr(df)
    assert t.tolist() == pytest.approx([1.0, 1.1])


def test_stray_lines_not_in_wrapped_name():
    text = ("Raportti 15.01.2026\nOmistukset\nSalkku yhteensä\niShares Blockchain Technology UCITS ETF\nUSD (Acc)\n"
            "10,00 EUR 12,00 20 200,00 \u221240,00 4,44%\n")
    h = parse_report_text(text, load_instruments())
    assert h.positions[0].name == "iShares Blockchain Technology UCITS ETF USD (Acc)"


def test_one_line_name_with_stray_line_above():
    text = "Raportti 15.01.2026\nOmistukset\nNordnet Suomi Indeksi\n340,00 EUR 320,00 6,5 2\u00a0210,00 +130,00 49,11%\n"
    h = parse_report_text(text, load_instruments())
    assert h.positions[0].name == "Nordnet Suomi Indeksi" and h.positions[0].ticker == "^OMXH25"
