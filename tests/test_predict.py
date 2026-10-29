from src import predict
from src.data_loader import generate_sample


def test_backtest_rates_in_range():
    df = generate_sample(days=90)
    for target in ("de", "loto", "kep", "cap"):
        bt = predict.backtest(df, target, k=5, warmup=60)
        assert set(bt.index) == {*predict.STRATEGIES, "ly_thuyet"}
        assert ((bt["ti_le"] >= 0) & (bt["ti_le"] <= 1)).all()
        assert (bt["p_holm"].dropna() >= bt["p"].dropna()).all()


def test_all_strategies_score_every_number():
    df = generate_sample(days=90)
    for target in ("de", "kep", "cap"):
        m = predict.analysis.matrix(df, target)
        for name, fn in predict.STRATEGIES.items():
            assert fn(m).shape == (m.shape[1],), name


def test_holm():
    import numpy as np
    assert np.allclose(predict.holm(np.array([0.01, 0.04, 0.03])), [0.03, 0.06, 0.06])


def test_predict_returns_k_unique_numbers():
    df = generate_sample(days=90)
    out = predict.predict(df, "kep", k=3)
    assert len(out) == 3 and out["so"].is_unique
    assert all(s[0] == s[1] for s in out["so"])


def test_report_written(tmp_path):
    from src.report import write_report
    df = generate_sample(days=90)
    path = write_report(df, predict.run(df, list(predict.analysis.TARGETS)), tmp_path / "r.html",
                        tracking_path=tmp_path / "p.csv")
    html = path.read_text(encoding="utf-8")
    assert "<svg" in html and 'id="k"' not in html
    assert "Đề 10 số" in html and "Cặp lộn 1 cặp" in html


def test_default_suggestion_counts():
    df = generate_sample(days=90)
    res = predict.run(df, list(predict.analysis.TARGETS))
    assert {t: len(r["predict"]) for t, r in res.items()} == {"loto": 3, "de": 10, "kep": 2, "cap": 1}
    assert all(len(p) == res[t]["k"] for t, r in res.items() for p in r["picks"].values())
    a, b = res["cap"]["predict"]["so"][0].split("-")
    assert a == b[::-1] and a < b
    assert predict.suggest_k(4) == {"loto": 4, "de": 4, "kep": 4, "cap": 4}


def test_theoretical():
    assert predict.theoretical("de", 10) == 0.1
    assert round(predict.theoretical("loto", 3), 4) == round(1 - 0.97 ** 27, 4)
    assert round(predict.theoretical("cap", 1), 4) == round(1 - 0.98 ** 27, 4)


def test_prize_table_groups():
    from src.report import prize_table
    html = prize_table([str(i) for i in range(27)])
    assert html.count("<tr") == 8
    assert "<td>Bảy</td><td>23 24 25 26</td>" in html
