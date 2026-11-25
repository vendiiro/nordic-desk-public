import pytest

from nordic_desk.signals import implied_return, load_signal_config, rating_share, size_label, status, thresholds


def test_config():
    assert load_signal_config() == {"buy_margin": 0.15, "thin_coverage": 5}


def test_thresholds():
    buy, sell = thresholds(115.0, 0.15)
    assert buy == pytest.approx(100.0) and sell == 115.0


@pytest.mark.parametrize("price,expected", [(99, "below buy threshold"), (110, "between thresholds"), (120, "above sell threshold")])
def test_status(price, expected):
    assert status(price, 100.0, 115.0, 20, 5) == expected


def test_status_thin_and_missing():
    assert status(99, 100.0, 115.0, 4, 5) == "thin coverage"
    assert status(99, None, None, 0, 5) == "no analyst coverage"


def test_size_label():
    assert size_label(3e12) == "large" and size_label(5e9) == "mid" and size_label(1e9) == "small" and size_label(None) is None


def test_rating_share():
    assert rating_share({"strongBuy": 5, "buy": 20, "hold": 4, "sell": 1, "strongSell": 0}) == pytest.approx(25 / 30)
    assert rating_share({"strongBuy": 0, "buy": 0, "hold": 0, "sell": 0, "strongSell": 0}) is None


def test_implied_return():
    value, covered = implied_return({"A": 0.5, "B": 0.3, "C": 0.2}, {"A": 0.10, "B": 0.20, "C": None})
    assert covered == pytest.approx(0.8)
    assert value == pytest.approx((0.5 * 0.10 + 0.3 * 0.20) / 0.8)
    assert implied_return({"C": 1.0}, {"C": None}) == (None, 0.0)
