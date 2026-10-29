"""Tải kết quả XSMB từ rongbachkim.com và lưu vào data/raw/results.csv."""
import argparse
import csv
import json
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

from .data_loader import DATA_FILE

API_URL = "https://rongbachkim.com/ketqua.php?getkq&ngay={ngay}&days={days}&wday=0"
MAX_DAYS = 300  # server giới hạn tối đa 300 kỳ quay mỗi request
DEFAULT_YEARS = 5
RETRIES = 3
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
    """Lấy tối đa `days` kỳ quay tính lùi từ `end` (gồm cả `end`), thử lại khi lỗi mạng."""
    url = API_URL.format(ngay=end.isoformat(), days=min(days, MAX_DAYS))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return parse_response(resp.read().decode("utf-8"))
        except (OSError, ValueError):
            if attempt == RETRIES - 1:
                raise
            time.sleep(2 ** attempt * 5)


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


def years_ago(years: int, today: date | None = None) -> date:
    today = today or today_vn()
    return today - timedelta(days=round(years * 365.25) - 1)


def update(days: int | None = None, path=DATA_FILE) -> tuple[int, list[str]]:
    """Cập nhật CSV, không bao giờ xoá dữ liệu đã có.

    - Lấy các kỳ mới hơn kỳ mới nhất trong file.
    - Nếu `days` được truyền (hoặc file rỗng: mặc định DEFAULT_YEARS năm) và dữ liệu chưa
      phủ đủ, tải bổ sung các kỳ cũ hơn kỳ cũ nhất trong file.
    Kỳ chưa đủ 27 số (đang quay) không được lưu để lần sau tải lại.
    Trả về (số ngày thêm mới, các ngày đang quay dở).
    """
    existing = {d: n for d, n in read_csv(path).items() if len(n) == PRIZES_PER_DAY}
    today = today_vn()
    if days is None and not existing:
        days = (today - years_ago(DEFAULT_YEARS, today)).days + 1

    new: list[tuple[str, list[str]]] = []
    if existing:
        latest, earliest = max(existing), min(existing)
        new += crawl((today - date.fromisoformat(latest)).days + 1, end=today, stop_after=latest)
        start = today - timedelta(days=days - 1) if days else None
        if start and start.isoformat() < earliest:
            end = date.fromisoformat(earliest) - timedelta(days=1)
            new += crawl((end - start).days + 1, end=end)
    else:
        new += crawl(days, end=today)

    pending = [d for d, n in new if len(n) != PRIZES_PER_DAY]
    added = {d: n for d, n in new if d not in existing and len(n) == PRIZES_PER_DAY}
    existing.update(added)
    save_csv(existing, path)
    return len(added), pending


def main():
    parser = argparse.ArgumentParser(description="Tải kết quả XSMB từ rongbachkim.com")
    parser.add_argument("--days", type=int,
                        help="đảm bảo có dữ liệu ít nhất N ngày lịch tính lùi từ hôm nay "
                             "(tải bổ sung kỳ cũ nếu thiếu; không bao giờ xoá dữ liệu)")
    parser.add_argument("--years", type=float, help="như --days nhưng tính theo năm")
    args = parser.parse_args()
    days = args.days
    if args.years:
        days = (today_vn() - years_ago(args.years)).days + 1
    added, pending = update(days)
    total = len(read_csv())
    print(f"Thêm {added} ngày mới. Tổng {total} kỳ trong {DATA_FILE}")
    if pending:
        print(f"Kỳ {', '.join(pending)} đang quay, chưa đủ 27 số — chưa lưu, hãy chạy lại sau.")


if __name__ == "__main__":
    main()
