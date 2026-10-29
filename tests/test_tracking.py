from datetime import datetime

import pandas as pd

from src import predict, tracking
from src.crawler import VN_TZ
from src.data_loader import generate_sample


def _setup(tmp_path):
    df = generate_sample(days=90)
    results = predict.run(df, ["de", "cap"])
    nxt = tracking.next_draw_date(df)
    morning = datetime(nxt.year, nxt.month, nxt.day, 9, tzinfo=VN_TZ)
    return df, results, tmp_path / "p.csv", morning


def test_record_once_per_draw_and_not_after_draw_time(tmp_path):
    df, results, path, morning = _setup(tmp_path)
    assert tracking.record(df, results, path, now=morning.replace(hour=18, minute=5)) == 0
    n = tracking.record(df, results, path, now=morning)
    assert n == 2 * len(predict.STRATEGIES)
    assert tracking.record(df, results, path, now=morning) == 0  # giữ bản ghi đầu tiên
    saved = tracking.load(path)
    combo = saved[(saved["target"] == "de") & (saved["strategy"] == "combo")]
    assert combo["numbers"].iloc[0] == " ".join(results["de"]["predict"]["so"])
    assert combo["k"].iloc[0] == 10
    cap = saved[(saved["target"] == "cap") & (saved["strategy"] == "combo")].iloc[0]
    assert cap["k"] == 1 and results["cap"]["predict"]["so"][0].startswith(cap["numbers"])
    assert (saved["date"] == tracking.next_draw_date(df)).all()


def test_score_and_summary(tmp_path):
    df, _, path, _ = _setup(tmp_path)
    d1, d2 = df["date"].iloc[-2], df["date"].iloc[-1]
    db1, db2 = df["db"].iloc[-2], df["db"].iloc[-1]
    preds = pd.DataFrame({
        "date": [d1, d2, d2 - pd.Timedelta(days=200), d2 + pd.Timedelta(days=1)],
        "target": ["de"] * 4, "strategy": ["combo"] * 4, "k": [5] * 4,
        "numbers": [f"{db1:02d}", f"{(db2 + 1) % 100:02d}", "00", "00"], "created_at": "x"})
    s = tracking.score(df, preds)
    assert s["trang_thai"].tolist() == ["da_cham", "da_cham", "khong_quay", "cho_ket_qua"]
    assert s["trung"].tolist()[:2] == [True, False] and s["trung_so"][0] == [db1]
    summ = tracking.summary(s).iloc[0]
    assert (summ["so_ky"], summ["trung"], summ["ti_le"]) == (2, 1, 0.5)


def test_report_shows_tracking(tmp_path):
    from src.report import write_report
    df, results, path, morning = _setup(tmp_path)
    html = write_report(df, results, tmp_path / "r.html", tracking_path=path).read_text()
    assert "Chưa có dự đoán nào" in html
    tracking.record(df, results, path, now=morning)
    html = write_report(df, results, tmp_path / "r.html", tracking_path=path).read_text()
    assert "Theo dõi dự đoán thực tế" in html and 'class="track"' in html and "chờ" in html


def test_evaluate_picks_match_predict():
    df = generate_sample(days=90)
    for t in ("de", "kep", "cap"):
        _, picks = predict.evaluate(df, t, 5)
        labels = [predict.analysis.label(t, n) for n in picks["combo"]]
        assert labels == predict.predict(df, t, 5)["so"].tolist()
        assert set(picks) == set(predict.STRATEGIES)
