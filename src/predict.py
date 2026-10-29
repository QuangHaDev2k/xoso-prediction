"""Các chiến lược "dự đoán" và backtest so sánh với ngẫu nhiên.

Chiến lược làm việc trên ma trận lịch sử M (số kỳ x số trong universe) để backtest nhanh.
"""
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

from . import analysis
from .data_loader import DATA_FILE, KEP, generate_sample, load_results

TARGET_NAMES = {
    "de": "2 số cuối giải Đặc biệt",
    "loto": "Loto (2 số cuối 27 giải)",
    "kep": "Lô kép (00, 11, ..., 99 trong 27 giải)",
    "dekep": "Đặc biệt về kép",
}


def _gan(m: np.ndarray) -> np.ndarray:
    """Số kỳ từ lần xuất hiện cuối của mỗi cột (chưa ra lần nào = số kỳ)."""
    hit = m > 0
    last = np.where(hit.any(0), len(m) - 1 - np.argmax(hit[::-1], axis=0), -1)
    return len(m) - 1 - last


def _max_gan(m: np.ndarray) -> np.ndarray:
    run = np.zeros(m.shape[1], dtype=int)
    best = run.copy()
    for row in m > 0:
        run = np.where(row, 0, run + 1)
        best = np.maximum(best, run)
    return best


def _norm(x: np.ndarray) -> np.ndarray:
    x = x.astype(float)
    span = x.max() - x.min()
    return (x - x.min()) / span if span else np.zeros_like(x)


def score_hot(m, window=30):
    """Ra nhiều trong `window` kỳ gần nhất."""
    return m[-window:].sum(0).astype(float)


def score_gan(m):
    """Lâu chưa ra nhất."""
    return _gan(m).astype(float)


def score_combo(m):
    """Kết hợp: tần suất ngắn hạn, tần suất dài hạn và mức gan so với gan cực đại."""
    gan_ratio = _gan(m) / np.maximum(_max_gan(m), 1)
    return 0.4 * _norm(m[-30:].sum(0)) + 0.3 * _norm(m.sum(0)) + 0.3 * np.clip(gan_ratio, 0, 1)


def score_random(m, rng=np.random.default_rng()):
    return rng.random(m.shape[1])


STRATEGIES = {"hot": score_hot, "gan": score_gan, "combo": score_combo, "random": score_random}


def _top(scores: np.ndarray, k: int) -> np.ndarray:
    # sắp xếp ổn định: hoà điểm thì ưu tiên số nhỏ hơn
    return np.argsort(-scores, kind="stable")[:k]


def theoretical(target: str, k: int) -> float:
    """Xác suất trúng >= 1 số khi chọn ngẫu nhiên k số (giả sử mỗi giải độc lập, đều)."""
    if target in ("de", "dekep"):
        return k / 100
    return 1 - (1 - k / 100) ** 27


def predict(df: pd.DataFrame, target: str = "de", k: int = 5, strategy: str = "combo") -> pd.DataFrame:
    """Top-k số cho kỳ tới, kèm các chỉ số giải thích."""
    universe = analysis.universe(target)
    m = analysis.matrix(df, target)
    scores = STRATEGIES[strategy](m)
    idx = _top(scores, k)
    return pd.DataFrame({
        "so": [f"{universe[j]:02d}" for j in idx],
        "diem": scores[idx].round(3),
        "ra_30_ky": m[-30:].sum(0)[idx],
        "ra_tong": m.sum(0)[idx],
        "gan": _gan(m)[idx],
        "gan_max": _max_gan(m)[idx],
    })


def backtest(df: pd.DataFrame, target: str = "de", k: int = 5, warmup: int = 60) -> pd.Series:
    """Walk-forward: tỉ lệ kỳ trúng >= 1 số đã chọn, so với xác suất lý thuyết."""
    m = analysis.matrix(df, target)
    hits = {name: [] for name in STRATEGIES}
    for i in range(warmup, len(m)):
        history, actual = m[:i], m[i] > 0
        for name, fn in STRATEGIES.items():
            hits[name].append(bool(actual[_top(fn(history), k)].any()))
    result = pd.Series({name: float(np.mean(h)) if h else float("nan") for name, h in hits.items()})
    result["ly_thuyet"] = theoretical(target, k)
    return result


def kep_outlook(df: pd.DataFrame) -> dict:
    """Xác suất ĐB về kép theo thống kê và lý thuyết (10/100)."""
    stats = analysis.kep_stats(df)
    return {"thuc_te": stats["db_kep_rate"], "ly_thuyet": len(KEP) / 100,
            "gan": stats["db_kep_gan"], "lo_kep_moi_ky": stats["loto_kep_per_day"]}


def run(df: pd.DataFrame, targets: list[str], k: int) -> dict:
    """Chạy dự đoán + backtest cho các target, trả về dict dùng cho in ấn và báo cáo."""
    out = {}
    for t in targets:
        out[t] = {"predict": predict(df, t, k), "backtest": backtest(df, t, k)}
    return out


def actions_url() -> str:
    """Link tới workflow trên GitHub (khi chạy trong GitHub Actions), ngược lại chuỗi rỗng."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    return f"{server}/{repo}/actions/workflows/daily.yml" if repo else ""


def load_data(verbose: bool = True) -> pd.DataFrame:
    if DATA_FILE.exists():
        return load_results()
    if verbose:
        print(f"Không thấy {DATA_FILE}, dùng dữ liệu ngẫu nhiên mẫu (chạy `python -m src.crawler`).\n")
    return generate_sample()


def build_report(k: int = 5):
    """Tính dự đoán + backtest cho cả 4 loại và ghi báo cáo HTML. Trả về (df, results, path)."""
    from .report import write_report
    df = load_data(verbose=False)
    results = run(df, list(analysis.TARGETS), k)
    return df, results, write_report(df, results, k)


def main():
    parser = argparse.ArgumentParser(description="Thống kê & dự đoán XSMB")
    parser.add_argument("--target", choices=["all", *analysis.TARGETS], default="all")
    parser.add_argument("--k", type=int, default=5, help="số lượng số gợi ý")
    parser.add_argument("--report", action="store_true", help="xuất reports/report.html")
    parser.add_argument("--site", metavar="DIR",
                        help="xuất trang tĩnh DIR/index.html (cho GitHub Pages, không có nút)")
    args = parser.parse_args()

    df = load_data()
    targets = list(analysis.TARGETS) if args.target == "all" else [args.target]
    print(f"Dữ liệu: {len(df)} kỳ, {df['date'].min():%d/%m/%Y} → {df['date'].max():%d/%m/%Y}")
    results = run(df, targets, args.k)
    for t, r in results.items():
        _, p = analysis.uniformity_test(df, t)
        print(f"\n=== {TARGET_NAMES[t]} — chi-square p={p:.3f} ===")
        print(r["predict"].to_string(index=False))
        print(f"Backtest (tỉ lệ kỳ trúng ≥1 trong {args.k} số):")
        print(r["backtest"].round(3).to_string())

    ko = kep_outlook(df)
    print(f"\nĐB về kép: thực tế {ko['thuc_te']:.1%} | lý thuyết {ko['ly_thuyet']:.0%} | "
          f"đã {ko['gan']} kỳ chưa về kép | TB {ko['lo_kep_moi_ky']:.2f} lô kép/kỳ")

    if args.report:
        from .report import write_report
        print(f"\nĐã ghi báo cáo: {write_report(df, results, args.k)}")
    if args.site:
        from .report import write_report
        path = write_report(df, results, args.k, Path(args.site) / "index.html", actions_url())
        print(f"Đã ghi trang tĩnh: {path}")


if __name__ == "__main__":
    main()
