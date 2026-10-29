"""Sổ theo dõi dự đoán thực tế: ghi số gợi ý TRƯỚC mỗi kỳ quay, chấm điểm khi có kết quả.

Khác với backtest (giả lập trên quá khứ), sổ này chỉ chứa dự đoán được ghi trước giờ quay,
nên là thước đo trung thực nhất cho hệ thống.

    python -m src.tracking [--strategy combo] [--last 15]

data/predictions.csv: date (kỳ được dự đoán), target, strategy, k, numbers, created_at.
Cặp lộn được ghi bằng số nhỏ hơn của cặp (59 = cặp 59-95).
"""
import argparse
from datetime import datetime, time
from pathlib import Path

import pandas as pd
from scipy.stats import binomtest

from . import analysis
from .crawler import VN_TZ
from .data_loader import DATA_FILE

PRED_FILE = DATA_FILE.parent.parent / "predictions.csv"
COLUMNS = ["date", "target", "strategy", "k", "numbers", "created_at"]
DRAW_HOUR = 18  # XSMB quay lúc 18h15: từ 18h ngày quay không ghi dự đoán cho kỳ đó nữa
SYSTEM_STRATEGY = "combo"  # chiến lược dùng cho phần gợi ý


def next_draw_date(df: pd.DataFrame) -> pd.Timestamp:
    return df["date"].max() + pd.Timedelta(days=1)


def load(path: Path = PRED_FILE) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(path, parse_dates=["date"], dtype={"numbers": str})


def record(df: pd.DataFrame, results: dict, path: Path = PRED_FILE,
           now: datetime | None = None) -> int:
    """Ghi số gợi ý kỳ tới của mọi chiến lược. Mỗi (kỳ, loại, chiến lược, k) chỉ ghi một
    lần — giữ bản ghi đầu tiên. Không ghi khi đã tới giờ quay. Trả về số dòng đã ghi."""
    date = next_draw_date(df)
    now = now or datetime.now(VN_TZ)
    if now >= datetime.combine(date.date(), time(DRAW_HOUR), VN_TZ):
        return 0
    old = load(path)
    done = set(zip(old["date"], old["target"], old["strategy"], old["k"].astype(int)))
    rows = [{"date": date, "target": t, "strategy": s, "k": r["k"],
             "numbers": " ".join(f"{n:02d}" for n in nums),
             "created_at": now.strftime("%Y-%m-%d %H:%M")}
            for t, r in results.items() for s, nums in r["picks"].items()
            if (date, t, s, r["k"]) not in done]
    if rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        out = pd.concat([old, pd.DataFrame(rows)], ignore_index=True)
        out.sort_values(["date", "target", "strategy", "k"]).to_csv(
            path, index=False, date_format="%Y-%m-%d")
    return len(rows)


def score(df: pd.DataFrame, preds: pd.DataFrame) -> pd.DataFrame:
    """Thêm cột trung_so (các số gợi ý đã về), trung (>= 1 số về) và trang_thai:
    "da_cham", "cho_ket_qua", hoặc "khong_quay" (ngày nghỉ Tết, đã có kỳ sau mà không có kỳ này)."""
    actual = {t: dict(zip(df["date"], map(set, analysis.draws(df, t)))) for t in analysis.TARGETS}
    last = df["date"].max()
    out = preds[preds["target"].isin(analysis.TARGETS)].copy()  # bỏ loại không còn gợi ý
    out["so"] = out["numbers"].fillna("").str.split().map(lambda xs: [int(x) for x in xs])
    got = [actual[t].get(d) for t, d in zip(out["target"], out["date"])]
    out["trung_so"] = [[n for n in so if n in a] if a is not None else []
                       for so, a in zip(out["so"], got)]
    out["trung"] = out["trung_so"].map(bool)
    out["trang_thai"] = ["da_cham" if a is not None else "khong_quay" if d < last else "cho_ket_qua"
                         for a, d in zip(got, out["date"])]
    return out


def summary(scored: pd.DataFrame) -> pd.DataFrame:
    """Theo từng (loại, chiến lược, k): số kỳ đã chấm, số kỳ trúng, tỉ lệ,
    xác suất lý thuyết và p-value một phía (trúng nhiều hơn chọn bừa)."""
    from .predict import STRATEGIES, theoretical
    done = scored[scored["trang_thai"] == "da_cham"]
    rows = []
    for (t, s, k), g in done.groupby(["target", "strategy", done["k"].astype(int)], sort=False):
        n, x, p0 = len(g), int(g["trung"].sum()), theoretical(t, k)
        rows.append({"target": t, "strategy": s, "k": k, "so_ky": n, "trung": x, "ti_le": x / n,
                     "ly_thuyet": p0, "p": binomtest(x, n, p0, alternative="greater").pvalue})
    out = pd.DataFrame(rows, columns=["target", "strategy", "k", "so_ky", "trung", "ti_le",
                                      "ly_thuyet", "p"])
    # xếp theo thứ tự loại và chiến lược của hệ thống thay vì bảng chữ cái
    order = {name: i for i, name in enumerate([*analysis.TARGETS, *STRATEGIES])}
    return out.sort_values(["target", "strategy"], key=lambda c: c.map(order).fillna(len(order)),
                           ignore_index=True)


def report_data(df: pd.DataFrame, ks: dict[str, int], path: Path = PRED_FILE) -> dict:
    """Dữ liệu cho báo cáo: chỉ các dự đoán ghi với đúng số gợi ý hiện tại `ks` của mỗi loại."""
    scored = score(df, load(path))
    if len(scored):
        scored = scored[scored["k"].astype(int) == scored["target"].map(ks)]
    return {"summary": summary(scored), "scored": scored,
            "since": scored["date"].min() if len(scored) else None}


def main():
    from .predict import TARGET_NAMES, load_data, suggest_k
    parser = argparse.ArgumentParser(description="Thống kê dự đoán thực tế đã ghi trong sổ theo dõi")
    parser.add_argument("--k", type=int, help="xem dự đoán ghi với cùng N số cho mọi loại "
                                              "(mặc định: số gợi ý hiện tại của từng loại)")
    parser.add_argument("--strategy", default=SYSTEM_STRATEGY,
                        help="chiến lược xem chi tiết từng kỳ (mặc định combo = phần gợi ý)")
    parser.add_argument("--last", type=int, default=15, help="số kỳ gần nhất hiển thị chi tiết")
    args = parser.parse_args()

    df = load_data()
    ks = suggest_k(args.k)
    data = report_data(df, ks)
    scored, summ = data["scored"], data["summary"]
    if scored.empty:
        print(f"Chưa có dự đoán nào với số gợi ý {ks} trong {PRED_FILE}.\n"
              "Sổ được ghi mỗi lần chạy `python -m src.predict` hoặc bấm nút dự đoán trên trang.")
        return
    pending = scored.loc[scored["trang_thai"] == "cho_ket_qua", "date"].drop_duplicates()
    print(f"Theo dõi từ {data['since']:%d/%m/%Y}. "
          f"Đã chấm {scored.loc[scored['trang_thai'] == 'da_cham', 'date'].nunique()} kỳ"
          + (f", chờ kết quả: {', '.join(f'{d:%d/%m}' for d in pending)}" if len(pending) else ""))
    for t in analysis.TARGETS:
        s = summ[summ["target"] == t].set_index("strategy")
        if s.empty:
            continue
        print(f"\n=== {TARGET_NAMES[t]} — {ks[t]} {'cặp' if t == 'cap' else 'số'} ===")
        print(s[["so_ky", "trung", "ti_le", "ly_thuyet", "p"]].round(3).to_string())

    mine = scored[scored["strategy"] == args.strategy]
    dates = sorted(mine["date"].unique())[-args.last:]
    print(f"\nChi tiết {len(dates)} kỳ gần nhất của chiến lược {args.strategy}:")
    for d in dates:
        rows = mine[mine["date"] == d].set_index("target")
        cells = []
        for t in analysis.TARGETS:
            if t not in rows.index:
                continue
            r = rows.loc[t]
            mark = {"cho_ket_qua": "…", "khong_quay": "nghỉ"}.get(
                r["trang_thai"],
                "✓ " + " ".join(analysis.label(t, n) for n in r["trung_so"]) if r["trung"] else "✗")
            cells.append(f"{t}: {' '.join(analysis.label(t, n) for n in r['so'])} [{mark}]")
        print(f"  {pd.Timestamp(d):%d/%m/%Y}  " + " | ".join(cells))
    print("\nLưu ý: cần vài trăm kỳ mới đủ để phân biệt với may rủi (p < 0.05).")


if __name__ == "__main__":
    main()
