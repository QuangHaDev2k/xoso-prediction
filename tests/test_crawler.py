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
    monkeypatch.setattr(crawler, "crawl", lambda days, stop_after=None: [
        ("2026-10-27", full), ("2026-10-28", full), ("2026-10-29", full[:5])])
    added, pending = crawler.update(days=10_000, path=path)
    assert added == 1 and pending == ["2026-10-29"]
    assert sorted(read_csv(path)) == ["2026-10-27", "2026-10-28"]
