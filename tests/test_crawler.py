from datetime import date

from src.crawler import parse_response, read_csv, save_csv
from src.data_loader import load_results

SAMPLE = ('[["2026-10-28",["74175","18190","62731","30468","95839","63573","61608","11741","53427",'
          '"95088","4748","4683","0750","5861","5728","8517","1385","6152","3575","1561","001","997",'
          '"249","58","30","05","41"]]]')


def test_parse_response():
    rows = parse_response(SAMPLE)
    assert rows[0][0] == "2026-10-28"
    assert len(rows[0][1]) == 27
    assert rows[0][1][0] == "74175"
    assert parse_response("") == []


def test_csv_roundtrip_keeps_leading_zeros(tmp_path):
    path = tmp_path / "results.csv"
    save_csv(dict(parse_response(SAMPLE)), path)
    assert read_csv(path)["2026-10-28"][12] == "0750"
    df = load_results(path)
    assert df["db"].iloc[0] == 75
    assert df["numbers"].iloc[0][-1] == 41


def test_update_skips_incomplete_day(tmp_path, monkeypatch):
    from src import crawler
    full = parse_response(SAMPLE)[0][1]
    path = tmp_path / "results.csv"
    save_csv({"2026-10-27": full}, path)
    monkeypatch.setattr(crawler, "today_vn", lambda: date(2026, 10, 29))
    monkeypatch.setattr(crawler, "crawl", lambda days, end=None, stop_after=None: [
        ("2026-10-27", full), ("2026-10-28", full), ("2026-10-29", full[:5])])
    added, pending = crawler.update(path=path)
    assert added == 1 and pending == ["2026-10-29"]
    assert sorted(read_csv(path)) == ["2026-10-27", "2026-10-28"]


def test_update_backfills_and_never_trims(tmp_path, monkeypatch):
    from src import crawler
    full = parse_response(SAMPLE)[0][1]
    path = tmp_path / "results.csv"
    save_csv({"2020-01-01": full, "2026-10-20": full}, path)
    calls = []

    def fake_crawl(days, end=None, stop_after=None):
        calls.append((days, end, stop_after))
        return [("2026-10-28", full)] if stop_after else [("2026-10-19", full), ("2026-10-15", full)]

    monkeypatch.setattr(crawler, "today_vn", lambda: date(2026, 10, 29))
    monkeypatch.setattr(crawler, "crawl", fake_crawl)
    # dữ liệu đã phủ từ 2020 -> không tải bổ sung, và không xoá kỳ 2020
    crawler.update(days=30, path=path)
    assert len(calls) == 1 and calls[0][2] == "2026-10-20"
    assert "2020-01-01" in read_csv(path)

    save_csv({"2026-10-20": full}, path)
    calls.clear()
    added, _ = crawler.update(days=15, path=path)
    assert calls[1] == (5, date(2026, 10, 19), None)   # 15/10 → 19/10
    assert added == 3 and min(read_csv(path)) == "2026-10-15"
