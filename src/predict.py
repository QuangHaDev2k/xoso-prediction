"""Các chiến lược "dự đoán" và backtest so sánh với ngẫu nhiên.

Chiến lược làm việc trên ma trận lịch sử M (số kỳ x số trong universe) để backtest nhanh.
"""
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, rankdata

from . import analysis
from .data_loader import DATA_FILE, KEP, generate_sample, load_results

TARGET_NAMES = {
    "de": "2 số cuối giải Đặc biệt",
    "loto": "Loto (2 số cuối 27 giải)",
    "kep": "Lô kép (00, 11, ..., 99 trong 27 giải)",
    "cap": "Cặp lô lộn (59-95, ... trong 27 giải)",
}

# Số lượng gợi ý mặc định cho từng loại (cặp lộn: số cặp)
SUGGEST_K = {"loto": 3, "de": 10, "kep": 2, "cap": 1}


def _runs(m: np.ndarray) -> np.ndarray:
    """runs[t, j] = số kỳ liên tiếp số j chưa ra tính đến hết kỳ t (vừa ra ở kỳ t = 0)."""
    t = np.arange(len(m))[:, None]
    last = np.maximum.accumulate(np.where(m > 0, t, -1), axis=0)
    return t - last


def _gan(m: np.ndarray) -> np.ndarray:
    """Số kỳ từ lần xuất hiện cuối của mỗi cột (chưa ra lần nào = số kỳ)."""
    return _runs(m)[-1] if len(m) else np.zeros(m.shape[1], dtype=int)


def _max_gan(m: np.ndarray) -> np.ndarray:
    return _runs(m).max(0) if len(m) else np.zeros(m.shape[1], dtype=int)


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


def score_ewma(m, half_life=20):
    """Tần suất có trọng số giảm dần: kỳ cách đây `half_life` kỳ chỉ tính một nửa."""
    w = 0.5 ** (np.arange(len(m))[::-1] / half_life)
    return w @ m


def score_bayes(m, prior=5.0):
    """Kỳ vọng hậu nghiệm Dirichlet: tần suất tổng được "co" về phân bố đều."""
    c = m.sum(0)
    return (c + prior) / (c.sum() + prior * len(c))


def score_markov(m, alpha=1.0):
    """Xích Markov bậc 1: P(số ra kỳ tới | các số ra kỳ vừa rồi), làm trơn Laplace."""
    x = (m > 0).astype(float)
    if len(x) < 2 or not x[-1].any():
        return score_bayes(m)
    t = x[:-1].T @ x[1:] + alpha
    return x[-1] @ (t / t.sum(1, keepdims=True))


def score_digit(m, window=60):
    """Tách đầu/đuôi: P(đầu) × P(đuôi) trong `window` kỳ (universe kép thì dùng bayes)."""
    if m.shape[1] != 100:
        return score_bayes(m)
    c = m[-window:].sum(0).reshape(10, 10)
    dau, duoi = c.sum(1) + 1, c.sum(0) + 1
    return np.outer(dau / dau.sum(), duoi / duoi.sum()).ravel()


def score_hazard(m):
    """Hàm rủi ro theo gan: tỉ lệ thực tế một số ra khi đã gan g kỳ (gộp mọi số)."""
    runs = _runs(m)
    before = np.vstack([np.zeros((1, m.shape[1]), dtype=int), runs[:-1]])  # gan trước mỗi kỳ
    seen = np.bincount(before.ravel(), minlength=len(m) + 1)
    came = np.bincount(before[m > 0], minlength=len(m) + 1)
    return ((came + 1) / (seen + 2))[_gan(m)]


def score_random(m, rng=np.random.default_rng()):
    return rng.random(m.shape[1])


# Chiến lược cơ sở: mỗi hàm nhận ma trận lịch sử, trả về điểm cho từng số
BASE = {"hot": score_hot, "gan": score_gan, "combo": score_combo, "ewma": score_ewma,
        "bayes": score_bayes, "markov": score_markov, "digit": score_digit,
        "hazard": score_hazard}

HEDGE_ETA = 1.0   # tốc độ học của hedge, chia cho √(số kỳ đã học)
HEDGE_K = 10      # thưởng = số lượt trúng trong top-HEDGE_K của mỗi chiến lược cơ sở
WARMUP = 60


def _rank01(x: np.ndarray) -> np.ndarray:
    """Đổi điểm thành hạng trong [0, 1] để cộng được các chiến lược khác thang đo."""
    return (rankdata(x) - 1) / max(len(x) - 1, 1)


def _base_scores(m: np.ndarray) -> np.ndarray:
    return np.array([fn(m) for fn in BASE.values()])


def _rewards(scores: np.ndarray, actual: np.ndarray) -> np.ndarray:
    """Lượt trúng của top-HEDGE_K mỗi chiến lược, trừ mức kỳ vọng khi chọn bừa."""
    k = min(HEDGE_K, scores.shape[1])
    got = np.array([actual[_top(s, k)].sum() for s in scores])
    return got - k * actual.sum() / scores.shape[1]


def _hedge_weights(cum: np.ndarray, steps: int) -> np.ndarray:
    """Trọng số ∝ exp(η · tổng thưởng / √steps): η giảm dần để dữ liệu dài không làm trọng số
    dồn hết vào chiến lược may mắn nhất."""
    w = np.exp(HEDGE_ETA * (cum - cum.max()) / np.sqrt(max(steps, 1)))
    return w / w.sum()


def score_ensemble(m):
    """Bỏ phiếu Borda: trung bình hạng của mọi chiến lược cơ sở."""
    return np.mean([_rank01(s) for s in _base_scores(m)], axis=0)


def score_hedge(m, warmup=WARMUP):
    """Trọng số nhân (Hedge): chiến lược nào trúng nhiều hơn chọn bừa thì được tăng trọng số."""
    cum = np.zeros(len(BASE))
    for i in range(warmup, len(m)):
        cum += _rewards(_base_scores(m[:i]), m[i])
    steps = max(len(m) - warmup, 0)
    return _hedge_weights(cum, steps) @ np.array([_rank01(s) for s in _base_scores(m)])


STRATEGIES = {**BASE, "ensemble": score_ensemble, "hedge": score_hedge, "random": score_random}


def _top(scores: np.ndarray, k: int) -> np.ndarray:
    # sắp xếp ổn định: hoà điểm thì ưu tiên số nhỏ hơn
    return np.argsort(-scores, kind="stable")[:k]


def holm(p: np.ndarray) -> np.ndarray:
    """Hiệu chỉnh Holm cho nhiều phép kiểm định cùng lúc."""
    order = np.argsort(p)
    adj = np.maximum.accumulate((len(p) - np.arange(len(p))) * p[order])
    out = np.empty_like(adj)
    out[order] = np.minimum(adj, 1)
    return out


def theoretical(target: str, k: int) -> float:
    """Xác suất trúng >= 1 số khi chọn ngẫu nhiên k số (giả sử mỗi giải độc lập, đều).
    Với cặp lộn, k cặp = 2k con số."""
    if target in ("de", "dekep"):
        return k / 100
    per_prize = 2 * k / 100 if target == "cap" else k / 100
    return 1 - (1 - per_prize) ** 27


def predict(df: pd.DataFrame, target: str = "de", k: int = 5, strategy: str = "combo") -> pd.DataFrame:
    """Top-k số cho kỳ tới, kèm các chỉ số giải thích."""
    universe = analysis.universe(target)
    m = analysis.matrix(df, target)
    scores = STRATEGIES[strategy](m)
    idx = _top(scores, k)
    return pd.DataFrame({
        "so": [analysis.label(target, universe[j]) for j in idx],
        "diem": scores[idx].round(3),
        "ra_30_ky": m[-30:].sum(0)[idx],
        "ra_tong": m.sum(0)[idx],
        "gan": _gan(m)[idx],
        "gan_max": _max_gan(m)[idx],
    })


def evaluate(df: pd.DataFrame, target: str = "de", k: int = 5,
             warmup: int = WARMUP) -> tuple[pd.DataFrame, dict[str, list[int]]]:
    """Walk-forward: tỉ lệ kỳ trúng >= 1 số đã chọn, p-value một phía so với xác suất lý
    thuyết và p-value đã hiệu chỉnh Holm (vì so sánh nhiều chiến lược cùng lúc).

    Bước cuối dùng toàn bộ dữ liệu để chọn k số cho kỳ tới của mọi chiến lược
    (trả về dạng {chiến lược: [số, ...]}), nên không phải tính lại hedge.
    """
    m = analysis.matrix(df, target)
    universe = analysis.universe(target)
    hits = {name: [] for name in STRATEGIES}
    cum = np.zeros(len(BASE))
    for i in range(min(warmup, len(m)), len(m) + 1):
        history = m[:i]
        base = _base_scores(history)
        ranks = np.array([_rank01(s) for s in base])
        scores = {**dict(zip(BASE, base)), "ensemble": ranks.mean(0),
                  "hedge": _hedge_weights(cum, i - warmup) @ ranks, "random": score_random(history)}
        if i == len(m):
            picks = {name: [universe[j] for j in _top(s, k)] for name, s in scores.items()}
            break
        actual = m[i]
        for name, s in scores.items():
            hits[name].append(bool(actual[_top(s, k)].any()))
        cum += _rewards(base, actual)
    p0 = theoretical(target, k)
    rate = pd.Series({name: float(np.mean(h)) if h else float("nan") for name, h in hits.items()})
    p = pd.Series({name: binomtest(sum(h), len(h), p0, alternative="greater").pvalue
                   if h else float("nan") for name, h in hits.items()})
    out = pd.DataFrame({"ti_le": rate, "p": p, "p_holm": holm(p.values)})
    out.loc["ly_thuyet"] = [p0, float("nan"), float("nan")]
    return out, picks


def backtest(df: pd.DataFrame, target: str = "de", k: int = 5, warmup: int = WARMUP) -> pd.DataFrame:
    return evaluate(df, target, k, warmup)[0]


def kep_outlook(df: pd.DataFrame) -> dict:
    """Xác suất ĐB về kép theo thống kê và lý thuyết (10/100)."""
    stats = analysis.kep_stats(df)
    return {"thuc_te": stats["db_kep_rate"], "ly_thuyet": len(KEP) / 100,
            "gan": stats["db_kep_gan"], "lo_kep_moi_ky": stats["loto_kep_per_day"]}


def suggest_k(k: int | None = None) -> dict[str, int]:
    """Số gợi ý cho từng loại: mặc định SUGGEST_K, hoặc cùng một k cho mọi loại."""
    return {t: k for t in SUGGEST_K} if k else dict(SUGGEST_K)


def run(df: pd.DataFrame, targets: list[str], ks: dict[str, int] | None = None) -> dict:
    """Chạy dự đoán + backtest cho các target, trả về dict dùng cho in ấn và báo cáo.
    "k" = số gợi ý của loại đó; "picks" = số gợi ý kỳ tới của mọi chiến lược (để ghi sổ)."""
    ks = {**SUGGEST_K, **(ks or {})}
    out = {}
    for t in targets:
        bt, picks = evaluate(df, t, ks[t])
        out[t] = {"predict": predict(df, t, ks[t]), "backtest": bt, "picks": picks, "k": ks[t]}
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


def build_report():
    """Tính dự đoán + backtest cho cả 4 loại và ghi báo cáo HTML. Trả về (df, results, path)."""
    from . import tracking
    from .report import write_report
    df = load_data(verbose=False)
    results = run(df, list(analysis.TARGETS))
    tracking.record(df, results)
    return df, results, write_report(df, results)


def main():
    parser = argparse.ArgumentParser(description="Thống kê & dự đoán XSMB")
    parser.add_argument("--target", choices=["all", *analysis.TARGETS], default="all")
    parser.add_argument("--k", type=int,
                        help="dùng cùng N số gợi ý cho mọi loại (mặc định: loto 3, đề 10, "
                             "kép 2, cặp lộn 1 cặp)")
    parser.add_argument("--report", action="store_true", help="xuất reports/report.html")
    parser.add_argument("--site", metavar="DIR",
                        help="xuất trang tĩnh DIR/index.html (cho GitHub Pages, không có nút)")
    parser.add_argument("--no-record", action="store_true",
                        help="không ghi dự đoán vào sổ theo dõi data/predictions.csv")
    args = parser.parse_args()

    df = load_data()
    targets = list(analysis.TARGETS) if args.target == "all" else [args.target]
    print(f"Dữ liệu: {len(df)} kỳ, {df['date'].min():%d/%m/%Y} → {df['date'].max():%d/%m/%Y}")
    results = run(df, targets, suggest_k(args.k))
    for t, r in results.items():
        _, p = analysis.uniformity_test(df, t)
        print(f"\n=== {TARGET_NAMES[t]} — chi-square p={p:.3f} ===")
        print(r["predict"].to_string(index=False))
        unit = "cặp" if t == "cap" else "số"
        print(f"Backtest (tỉ lệ kỳ trúng ≥1 trong {r['k']} {unit}; p_holm < 0.05 mới đáng chú ý):")
        print(r["backtest"].round(3).to_string(na_rep=""))

    if not args.no_record:
        from . import tracking
        n = tracking.record(df, results)
        if n:
            print(f"\nĐã ghi {n} dự đoán kỳ {tracking.next_draw_date(df):%d/%m/%Y} vào {tracking.PRED_FILE}")

    ko = kep_outlook(df)
    print(f"\nĐB về kép: thực tế {ko['thuc_te']:.1%} | lý thuyết {ko['ly_thuyet']:.0%} | "
          f"đã {ko['gan']} kỳ chưa về kép | TB {ko['lo_kep_moi_ky']:.2f} lô kép/kỳ")

    if args.report:
        from .report import write_report
        print(f"\nĐã ghi báo cáo: {write_report(df, results)}")
    if args.site:
        from .report import write_report
        path = write_report(df, results, Path(args.site) / "index.html", actions_url())
        print(f"Đã ghi trang tĩnh: {path}")


if __name__ == "__main__":
    main()
