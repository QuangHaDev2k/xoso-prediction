"""Đọc dữ liệu kết quả xổ số."""
from pathlib import Path

import numpy as np
import pandas as pd

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "raw" / "results.csv"

KEP = [d * 11 for d in range(10)]  # 00, 11, ..., 99


def load_results(path: Path = DATA_FILE) -> pd.DataFrame:
    """Trả về DataFrame: date, prizes (list[str] - 27 số đầy đủ), numbers (list[int] - 2 số
    cuối 27 giải), db (2 số cuối ĐB).

    CSV lưu số đầy đủ theo thứ tự giải, số đầu tiên là giải Đặc biệt.
    """
    df = pd.read_csv(path, parse_dates=["date"], dtype={"numbers": str})
    df["prizes"] = df["numbers"].str.split()
    df["numbers"] = df["prizes"].apply(lambda xs: [int(x) % 100 for x in xs])
    df["db"] = df["numbers"].str[0]
    return df.sort_values("date").reset_index(drop=True)


def generate_sample(days: int = 365, per_day: int = 27, seed: int = 0) -> pd.DataFrame:
    """Sinh dữ liệu ngẫu nhiên giả lập XSMB (27 giải/ngày, giải đầu là ĐB) để chạy thử."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days)
    numbers = [rng.integers(0, 100, per_day).tolist() for _ in dates]
    return pd.DataFrame({"date": dates, "numbers": numbers, "db": [n[0] for n in numbers],
                         "prizes": [[f"{n:02d}" for n in ns] for ns in numbers]})
