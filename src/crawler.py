"""Tải kết quả XSMB từ rongbachkim.com và lưu vào data/raw/results.csv."""
import argparse
import csv
import json
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

from .data_loader import DATA_FILE

API_URL = "https://rongbachkim.com/ketqua.php?getkq&ngay={ngay}&days={days}&wday=0"
MAX_DAYS = 300  # server giới hạn tối đa 300 ngày mỗi request
PRIZES_PER_DAY = 27
VN_TZ = timezone(timedelta(hours=7))  # giờ Việt Nam, không có giờ mùa hè


def today_vn() -> date:
    """Ngày hiện tại theo giờ Việt Nam (máy chủ GitHub Actions chạy giờ UTC)."""
    return datetime.now(VN_TZ).date()


def parse_response(text: str) -> list[tuple[str, list[str]]]:
    """JSON dạng [["YYYY-MM-DD", ["ĐB", "G1", ... 27 số]], ...] -> list (date, numbers)."""
    if not text.strip():
        return []
    return [(day, [str(n) for n in nums]) for day, nums in json.loads(text)]


def fetch_range(end: date, days: int) -> list[tuple[str, list[str]]]:
    """Lấy `days` ngày quay thưởng tính lùi từ `end` (gồm cả `end`)."""
    url = API_URL.format(ngay=end.isoformat(), days=min(days, MAX_DAYS))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return parse_response(resp.read().decode("utf-8"))


def crawl(days: int = 365, end: date | None = None, stop_after: str | None = None,
          delay: float = 1.0) -> list[tuple[str, list[str]]]:
    """Lấy kết quả trong `days` ngày lịch tính lùi từ `end`; dừng sớm khi gặp ngày <= stop_after."""
    end = end or today_vn()
    start = end - timedelta(days=days - 1)
    results: dict[str, list[str]] = {}
    cursor = end
    while cursor >= start:
        chunk = (cursor - start).days + 1
        rows = fetch_range(cursor, chunk)
        if not rows:
            break
        for day, nums in rows:
            if day >= start.isoformat():
                results[day] = nums
        oldest = min(day for day, _ in rows)
        if stop_after and oldest <= stop_after:
            break
        cursor = date.fromisoformat(oldest) - timedelta(days=1)
        time.sleep(delay)

    return sorted(results.items())


def read_csv(path=DATA_FILE) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {row["date"]: row["numbers"].split() for row in csv.DictReader(f)}


def save_csv(rows: dict[str, list[str]], path=DATA_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "numbers"])
        for day in sorted(rows):
            w.writerow([day, " ".join(rows[day])])


def update(days: int = 365, path=DATA_FILE) -> tuple[int, list[str]]:
    """Cập nhật CSV: nếu đã có dữ liệu thì chỉ lấy các ngày mới.

    Kỳ chưa đủ 27 số (đang quay) không được lưu để lần sau tải lại.
    Trả về (số ngày thêm mới, các ngày đang quay dở).
    """
    existing = {d: n for d, n in read_csv(path).items() if len(n) == PRIZES_PER_DAY}
    latest = max(existing) if existing else None
    new = crawl(days, stop_after=latest)
    pending = [d for d, n in new if len(n) != PRIZES_PER_DAY]
    added = {d: n for d, n in new if d not in existing and len(n) == PRIZES_PER_DAY}
    existing.update(added)
    # chỉ giữ cửa sổ `days` ngày gần nhất
    cutoff = (today_vn() - timedelta(days=days - 1)).isoformat()
    save_csv({d: n for d, n in existing.items() if d >= cutoff}, path)
    return len(added), pending


def main():
    parser = argparse.ArgumentParser(description="Tải kết quả XSMB từ rongbachkim.com")
    parser.add_argument("--days", type=int, default=365, help="số ngày lịch tính lùi từ hôm nay")
    args = parser.parse_args()
    added, pending = update(args.days)
    total = len(read_csv())
    print(f"Thêm {added} ngày mới. Tổng {total} kỳ trong {DATA_FILE}")
    if pending:
        print(f"Kỳ {', '.join(pending)} đang quay, chưa đủ 27 số — chưa lưu, hãy chạy lại sau.")


if __name__ == "__main__":
    main()
