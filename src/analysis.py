"""Các phép thống kê trên kết quả xổ số.

`target` chọn chuỗi số dùng cho mỗi kỳ:
- "loto": 2 số cuối của cả 27 giải
- "de":   2 số cuối giải Đặc biệt
- "kep":  các lô kép (00, 11, ..., 99) trong 27 giải
- "dekep": giải Đặc biệt khi 2 số cuối là kép
"""
from collections import Counter

import numpy as np
import pandas as pd
from scipy.stats import chisquare

from .data_loader import KEP

TARGETS = ("loto", "de", "kep", "dekep")


def universe(target: str = "loto") -> list[int]:
    """Tập số có thể ra với mỗi target."""
    return KEP if target in ("kep", "dekep") else list(range(100))


def draws(df: pd.DataFrame, target: str = "loto") -> list[list[int]]:
    """Danh sách số mỗi kỳ theo target."""
    if target == "loto":
        return list(df["numbers"])
    if target == "de":
        return [[n] for n in df["db"]]
    if target == "kep":
        return [[n for n in nums if n in KEP] for nums in df["numbers"]]
    if target == "dekep":
        return [[n] if n in KEP else [] for n in df["db"]]
    raise ValueError(f"target không hợp lệ: {target}")


def matrix(df: pd.DataFrame, target: str = "loto") -> np.ndarray:
    """Ma trận số lần xuất hiện, shape (số kỳ, len(universe(target)))."""
    pos = {n: j for j, n in enumerate(universe(target))}
    m = np.zeros((len(df), len(pos)), dtype=int)
    for i, nums in enumerate(draws(df, target)):
        for n in nums:
            m[i, pos[n]] += 1
    return m


def frequency(df: pd.DataFrame, target: str = "loto", window: int | None = None) -> pd.Series:
    """Số lần xuất hiện của mỗi số (trong `window` kỳ gần nhất nếu có)."""
    rows = draws(df, target)
    if window:
        rows = rows[-window:]
    counts = pd.Series([n for nums in rows for n in nums], dtype=int).value_counts()
    return counts.reindex(universe(target), fill_value=0)


def gan(df: pd.DataFrame, target: str = "loto") -> pd.Series:
    """Lô gan: số kỳ liên tiếp gần nhất mà mỗi số chưa xuất hiện."""
    last_seen = {n: -1 for n in universe(target)}
    for i, nums in enumerate(draws(df, target)):
        for n in nums:
            last_seen[n] = i
    total = len(df)
    return pd.Series({n: total - 1 - i for n, i in last_seen.items()}).sort_values(ascending=False)


def max_gan(df: pd.DataFrame, target: str = "loto") -> pd.Series:
    """Gan cực đại: chuỗi kỳ dài nhất mỗi số không xuất hiện trong lịch sử."""
    current = {n: 0 for n in universe(target)}
    best = dict(current)
    for nums in draws(df, target):
        hit = set(nums)
        for n in current:
            current[n] = 0 if n in hit else current[n] + 1
            best[n] = max(best[n], current[n])
    return pd.Series(best)


def dau_duoi(df: pd.DataFrame, target: str = "de", window: int | None = None) -> pd.DataFrame:
    """Tần suất chữ số đầu (hàng chục) và đuôi (hàng đơn vị) 0-9."""
    rows = draws(df, target)
    if window:
        rows = rows[-window:]
    flat = [n for nums in rows for n in nums]
    dau = Counter(n // 10 for n in flat)
    duoi = Counter(n % 10 for n in flat)
    return pd.DataFrame({"dau": [dau[d] for d in range(10)],
                         "duoi": [duoi[d] for d in range(10)]})


def de_profile(df: pd.DataFrame) -> dict:
    """Tỉ lệ chẵn/lẻ, to (>=50)/nhỏ và phân bố tổng 2 chữ số (mod 10) của ĐB."""
    db = df["db"]
    tong = ((db // 10 + db % 10) % 10).value_counts().reindex(range(10), fill_value=0)
    return {
        "chan": float((db % 2 == 0).mean()),
        "le": float((db % 2 == 1).mean()),
        "to": float((db >= 50).mean()),
        "nho": float((db < 50).mean()),
        "tong": tong,
    }


def kep_stats(df: pd.DataFrame) -> dict:
    """Thống kê kép: tỉ lệ ĐB về kép, số lô kép trung bình mỗi kỳ, kép gan."""
    kep_db = df["db"].isin(KEP)
    since = len(df) - 1 - kep_db[kep_db].index.max() if kep_db.any() else len(df)
    return {
        "db_kep_rate": float(kep_db.mean()),
        "db_kep_gan": int(since),
        "db_kep_dates": df.loc[kep_db, ["date", "db"]].tail(10),
        "loto_kep_per_day": sum(map(len, draws(df, "kep"))) / max(len(df), 1),
        "loto_kep_gan": gan(df, "kep"),
    }


def nhay(df: pd.DataFrame, window: int | None = 30, min_times: int = 2) -> pd.Series:
    """Số lần mỗi lô về >= `min_times` nháy trong 1 kỳ (trong `window` kỳ gần nhất)."""
    rows = list(df["numbers"])[-window:] if window else list(df["numbers"])
    counts = Counter(n for nums in rows for n, c in Counter(nums).items() if c >= min_times)
    return pd.Series(counts, dtype=int).sort_values(ascending=False)


def follow_db(df: pd.DataFrame, by: str = "duoi") -> pd.DataFrame:
    """Bảng chuyển tiếp: đuôi (hoặc đầu) ĐB hôm nay -> phân bố đuôi (đầu) ĐB kỳ kế tiếp."""
    key = (lambda n: n % 10) if by == "duoi" else (lambda n: n // 10)
    db = [key(n) for n in df["db"]]
    table = pd.DataFrame(0, index=range(10), columns=range(10))
    for a, b in zip(db, db[1:]):
        table.loc[a, b] += 1
    return table


def uniformity_test(df: pd.DataFrame, target: str = "loto"):
    """Chi-square: kiểm tra phân bố có đều không. p-value lớn => không có bằng chứng lệch."""
    return chisquare(frequency(df, target).values)
