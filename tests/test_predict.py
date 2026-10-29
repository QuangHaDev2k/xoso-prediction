from src import predict
from src.data_loader import generate_sample


def test_backtest_rates_in_range():
    df = generate_sample(days=90)
    for target in ("de", "loto", "kep", "dekep"):
        bt = predict.backtest(df, target, k=5, warmup=60)
        assert set(bt.index) == {*predict.STRATEGIES, "ly_thuyet"}
        assert ((bt >= 0) & (bt <= 1)).all()


def test_predict_returns_k_unique_numbers():
    df = generate_sample(days=90)
    out = predict.predict(df, "kep", k=3)
    assert len(out) == 3 and out["so"].is_unique
    assert all(s[0] == s[1] for s in out["so"])


def test_report_written(tmp_path):
    from src.report import write_report
    df = generate_sample(days=90)
    path = write_report(df, predict.run(df, ["de", "loto"], 5), 5, tmp_path / "r.html")
    assert "<svg" in path.read_text(encoding="utf-8")


def test_prize_table_groups():
    from src.report import prize_table
    html = prize_table([str(i) for i in range(27)])
    assert html.count("<tr") == 8
    assert "<td>Bảy</td><td>23 24 25 26</td>" in html


def test_server_parse_k():
    import pytest
    from src.server import _parse_k
    assert _parse_k("k=7") == 7
    with pytest.raises(ValueError):
        _parse_k("k=0")
