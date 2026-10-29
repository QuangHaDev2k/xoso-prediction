"""Sinh báo cáo HTML tự chứa (SVG inline, không phụ thuộc thư viện ngoài)."""
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd

from . import analysis, tracking
from .crawler import VN_TZ
from .predict import TARGET_NAMES, kep_outlook

REPORT_FILE = Path(__file__).resolve().parent.parent / "reports" / "report.html"

STRATEGY_NAMES = {"hot": "Hot (ra nhiều 30 kỳ)", "gan": "Gan (lâu chưa ra)",
                  "combo": "Kết hợp", "ewma": "Tần suất giảm dần (EWMA)",
                  "bayes": "Bayes (Dirichlet)", "markov": "Markov (theo kỳ trước)",
                  "digit": "Đầu × đuôi", "hazard": "Rủi ro theo gan",
                  "ensemble": "Bỏ phiếu (Borda)", "hedge": "Trọng số thích ứng (Hedge)",
                  "random": "Ngẫu nhiên", "ly_thuyet": "Xác suất lý thuyết"}


def bar_chart(labels: list[str], values: list[float], highlight: set[str] = frozenset(),
              unit: str = "lần", width: int = 360, height: int = 220) -> str:
    """Biểu đồ cột SVG; cột thuộc `highlight` tô màu nhấn. Hover hiện tooltip."""
    n = len(labels)
    pad_l, pad_b, pad_t, gap = 32, 22, 10, 2
    slot = (width - pad_l) / n
    w_bar = slot - gap
    vmax = max(max(values), 1)
    plot_h = height - pad_b - pad_t
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    for frac in (0, 0.5, 1):
        y = pad_t + plot_h * (1 - frac)
        parts.append(f'<line x1="{pad_l}" x2="{width}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'
                     f'<text x="{pad_l - 6}" y="{y + 4:.1f}" class="tick" text-anchor="end">'
                     f'{vmax * frac:.0f}</text>')
    step = 1 if n <= 20 else 5
    for i, (lab, v) in enumerate(zip(labels, values)):
        x = pad_l + i * slot + gap / 2
        h = plot_h * v / vmax
        y = pad_t + plot_h - h
        cls = "bar hl" if lab in highlight else "bar"
        parts.append(f'<g class="hit" data-tip="{escape(lab)}: {v:g} {unit}">'
                     f'<rect x="{x - gap / 2:.1f}" y="{pad_t}" width="{slot:.1f}" height="{plot_h}" class="hitbox"/>'
                     f'<path class="{cls}" d="{_bar_path(x, y, w_bar, h)}"/></g>')
        if i % step == 0:
            parts.append(f'<text x="{x + w_bar / 2:.1f}" y="{height - 6}" class="tick" '
                         f'text-anchor="middle">{escape(lab)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _bar_path(x, y, w, h, r=4):
    """Cột bo góc 4px ở đầu dữ liệu, đáy vuông nằm trên trục."""
    if h <= 0:
        return ""
    r = min(r, w / 2, h)
    b = y + h
    return (f"M{x:.1f},{b:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} H{x + w - r:.1f} "
            f"Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} V{b:.1f} Z")


def table(df: pd.DataFrame, cls: str = "") -> str:
    head = "".join(f"<th>{escape(str(c))}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>"
                   for row in df.itertuples(index=False))
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


PRIZE_GROUPS = [("Đặc biệt", 1), ("Nhất", 1), ("Nhì", 2), ("Ba", 6),
                ("Tư", 4), ("Năm", 6), ("Sáu", 3), ("Bảy", 4)]


def prize_table(prizes: list[str]) -> str:
    """Bảng kết quả 1 kỳ theo từng giải (27 số theo thứ tự ĐB → G7)."""
    rows, i = [], 0
    for name, size in PRIZE_GROUPS:
        cls = ' class="db"' if i == 0 else ""
        rows.append(f"<tr{cls}><td>{name}</td><td>{escape(' '.join(prizes[i:i + size]))}</td></tr>")
        i += size
    return f'<table class="prizes"><tbody>{"".join(rows)}</tbody></table>'


def toolbar(next_date: str, actions_url: str | None) -> str:
    """Thanh nút. actions_url != None: trang tĩnh trên GitHub Pages, thay nút bằng link Run workflow."""
    if actions_url is not None:
        link = (f' Cập nhật ngay: bấm <a href="{escape(actions_url)}" target="_blank" rel="noopener">'
                f'Run workflow trên GitHub</a>.' if actions_url else "")
        return (f'<div class="toolbar"><span class="note">Trang tự cập nhật mỗi tối khoảng 18h40 '
                f'và 20h30 (giờ VN).{link}</span></div>')
    return f"""<div class="toolbar">
  <button id="btn-update" data-api="/api/update">⟳ Tải kết quả mới nhất</button>
  <button id="btn-predict" class="primary" data-api="/api/predict">Dự đoán kỳ {next_date}</button>
  <span id="status"></span>
</div>"""


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _pval(x: float) -> str:
    return "" if pd.isna(x) else f"{x:.2f}"


def _unit(target: str) -> str:
    return "cặp" if target == "cap" else "số"


def _prediction_card(target: str, r: dict) -> str:
    k = r["k"]
    pred = r["predict"].rename(columns={"so": "Số", "diem": "Điểm", "ra_30_ky": "Ra 30 kỳ",
                                        "ra_tong": "Ra tổng", "gan": "Gan", "gan_max": "Gan max"})
    balls = "".join(f'<span class="ball{" pair" if "-" in s else ""}">{s}</span>' for s in pred["Số"])
    bt = r["backtest"]
    bt_rows = pd.DataFrame({"Chiến lược": [STRATEGY_NAMES[s] for s in bt.index],
                            f"Tỉ lệ trúng ≥1/{k} {_unit(target)}": [_pct(v) for v in bt["ti_le"]],
                            "p (Holm)": [_pval(v) for v in bt["p_holm"]]})
    sys_rate, theory = bt.loc[tracking.SYSTEM_STRATEGY, "ti_le"], bt.loc["ly_thuyet", "ti_le"]
    return (f'<section class="card pick t-{target}">'
            f'<div class="pick-head"><h3>{TARGET_SHORT[target]}</h3>'
            f'<span class="badge">{k} {_unit(target)}</span></div>'
            f'<p class="sub">{escape(TARGET_NAMES[target])}</p>'
            f'<div class="balls">{balls}</div>'
            f'<div class="bt-line"><span>Backtest 5 năm</span><b>{_pct(sys_rate)}</b>'
            f'<span>chọn bừa {_pct(theory)}</span></div>'
            f'<details><summary>Chi tiết điểm</summary>{table(pred)}</details>'
            f'<details><summary>Backtest {len(bt) - 1} chiến lược</summary>'
            f'{table(bt_rows, "compact")}</details></section>')


TARGET_SHORT = {"de": "Đề", "loto": "Loto", "kep": "Lô kép", "cap": "Cặp lộn"}


def _picks_cell(row) -> str:
    """Các số gợi ý, số đã về được tô màu; kèm trạng thái."""
    if row is None:
        return "<td></td>"
    hit, lb = set(row["trung_so"]), lambda n: analysis.label(row["target"], n)
    nums = " ".join(f'<b class="got">{lb(n)}</b>' if n in hit else lb(n) for n in row["so"])
    tag = {"cho_ket_qua": '<span class="tag">chờ</span>', "khong_quay": '<span class="tag">nghỉ</span>'}
    mark = tag.get(row["trang_thai"], '<span class="tag ok">trúng</span>' if row["trung"] else "")
    return f"<td>{nums} {mark}</td>"


def tracking_section(df: pd.DataFrame, ks: dict[str, int], path: Path = tracking.PRED_FILE,
                     last: int = 15) -> str:
    """Thống kê sổ theo dõi: tỉ lệ trúng thực tế của phần gợi ý + chi tiết các kỳ gần nhất."""
    data = tracking.report_data(df, ks, path)
    scored, summ = data["scored"], data["summary"]
    if scored.empty:
        return ('<div class="card"><p class="meta">Chưa có dự đoán nào được ghi với số gợi ý hiện tại. '
                "Từ lần dự đoán tới, số gợi ý của mọi chiến lược sẽ được ghi lại trước giờ quay "
                "và chấm điểm khi có kết quả.</p></div>")
    n_done = scored.loc[scored["trang_thai"] == "da_cham", "date"].nunique()
    intro = (f'<p class="meta">Ghi từ kỳ {data["since"]:%d/%m/%Y} · {n_done} kỳ đã chấm · '
             f"chỉ tính dự đoán được ghi trước giờ quay (18h).</p>")

    mine = summ[summ["strategy"] == tracking.SYSTEM_STRATEGY]
    main_tbl = pd.DataFrame({
        "Loại": [f"{TARGET_SHORT[t]} ({k} {_unit(t)})" for t, k in zip(mine["target"], mine["k"])],
        "Số kỳ": mine["so_ky"], "Trúng": mine["trung"],
        "Tỉ lệ trúng": [_pct(v) for v in mine["ti_le"]],
        "Lý thuyết": [_pct(v) for v in mine["ly_thuyet"]],
        "p": [_pval(v) for v in mine["p"]]})
    all_tbl = pd.DataFrame({
        "Loại": [TARGET_SHORT[t] for t in summ["target"]],
        "Chiến lược": [STRATEGY_NAMES.get(x, x) for x in summ["strategy"]],
        "Số kỳ": summ["so_ky"], "Tỉ lệ": [_pct(v) for v in summ["ti_le"]],
        "Lý thuyết": [_pct(v) for v in summ["ly_thuyet"]], "p": [_pval(v) for v in summ["p"]]})

    sys_rows = scored[scored["strategy"] == tracking.SYSTEM_STRATEGY]
    dates = sorted(sys_rows["date"].unique(), reverse=True)[:last]
    by = {(d, t): r for d, t, r in zip(sys_rows["date"], sys_rows["target"], sys_rows.to_dict("records"))}
    head = "".join(f"<th>{TARGET_SHORT[t]}</th>" for t in analysis.TARGETS)
    body = "".join(f"<tr><td>{pd.Timestamp(d):%d/%m/%Y}</td>"
                   + "".join(_picks_cell(by.get((d, t))) for t in analysis.TARGETS) + "</tr>"
                   for d in dates)
    recent = (f'<table class="track"><thead><tr><th>Kỳ</th>{head}</tr></thead>'
              f"<tbody>{body}</tbody></table>")
    return (f'<div class="card">{intro}'
            f'<h3>Phần gợi ý (chiến lược "{STRATEGY_NAMES[tracking.SYSTEM_STRATEGY]}")</h3>'
            f'{table(main_tbl, "compact") if len(mine) else "<p class=meta>Chưa có kỳ nào được chấm.</p>"}'
            f"<details><summary>Tất cả chiến lược</summary>{table(all_tbl, 'compact')}</details>"
            f'<h4>{len(dates)} kỳ gần nhất · số <b class="got">tô màu</b> là số đã về</h4>'
            f'<div class="table-wrap">{recent}</div></div>')


def write_report(df: pd.DataFrame, results: dict, path: Path = REPORT_FILE,
                 actions_url: str | None = None, tracking_path: Path = tracking.PRED_FILE) -> Path:
    """Ghi báo cáo HTML. actions_url != None => bản tĩnh (không có nút gọi server)."""
    nums = [f"{n:02d}" for n in range(100)]
    picks = {t: set(r["predict"]["so"]) for t, r in results.items()}
    freq_de = analysis.frequency(df, "de")
    freq_loto = analysis.frequency(df, "loto")
    gan_loto = analysis.gan(df, "loto").head(20)
    gan_de = analysis.gan(df, "de").head(20)
    dd = analysis.dau_duoi(df, "de")
    prof = analysis.de_profile(df)
    ko = kep_outlook(df)
    kep_db = analysis.kep_stats(df)["db_kep_dates"]
    nhay = analysis.nhay(df, window=30).head(15)

    recent = df.tail(30).iloc[::-1]
    recent_tbl = pd.DataFrame({
        "Ngày": recent["date"].dt.strftime("%d/%m/%Y"),
        "ĐB": [f"{n:02d}" for n in recent["db"]],
        "Loto": [" ".join(f"{n:02d}" for n in sorted(ns)) for ns in recent["numbers"]],
    })

    cards = "".join(_prediction_card(t, r) for t, r in results.items())
    ks = {t: r["k"] for t, r in results.items()}
    charts = []
    if "de" in results:
        charts.append(("Tần suất 2 số cuối ĐB (00–99)",
                       bar_chart(nums, freq_de.tolist(), picks["de"], width=1200, height=220)))
    if "loto" in results:
        charts.append(("Tần suất loto (00–99)",
                       bar_chart(nums, freq_loto.tolist(), picks["loto"], width=1200, height=220)))
    charts += [
        ("Top 20 lô gan (số kỳ chưa ra)",
         bar_chart([f"{n:02d}" for n in gan_loto.index], gan_loto.tolist(), unit="kỳ")),
        ("Top 20 đề gan (số kỳ chưa ra; = số kỳ dữ liệu nghĩa là chưa ra lần nào)",
         bar_chart([f"{n:02d}" for n in gan_de.index], gan_de.tolist(), unit="kỳ")),
        ("Đầu ĐB (chữ số hàng chục)", bar_chart([str(d) for d in range(10)], dd["dau"].tolist())),
        ("Đuôi ĐB (chữ số hàng đơn vị)", bar_chart([str(d) for d in range(10)], dd["duoi"].tolist())),
    ]
    charts_html = "".join(
        f'<figure class="card{" wide" if "1200" in c[:40] else ""}"><figcaption>{escape(t)}</figcaption>{c}</figure>'
        for t, c in charts)

    stats = [
        ("ĐB về kép (thực tế)", _pct(ko["thuc_te"]), f"lý thuyết {ko['ly_thuyet']:.0%}"),
        ("Số kỳ ĐB chưa về kép", str(ko["gan"]), "kỳ"),
        ("Lô kép trung bình", f"{ko['lo_kep_moi_ky']:.2f}", "số/kỳ (lý thuyết 2.70)"),
        ("ĐB chẵn / lẻ", f"{prof['chan']:.0%} / {prof['le']:.0%}", ""),
        ("ĐB to / nhỏ", f"{prof['to']:.0%} / {prof['nho']:.0%}", "to = 50–99"),
    ]
    stats_html = "".join(f'<div class="stat"><div class="label">{escape(a)}</div>'
                         f'<div class="value">{escape(b)}</div><div class="sub">{escape(c)}</div></div>'
                         for a, b, c in stats)
    kep_tbl = pd.DataFrame({"Ngày": kep_db["date"].dt.strftime("%d/%m/%Y"),
                            "ĐB": [f"{n:02d}" for n in kep_db["db"]]}).iloc[::-1]
    nhay_tbl = pd.DataFrame({"Lô": [f"{n:02d}" for n in nhay.index],
                             "Số kỳ về ≥2 nháy": nhay.values})

    last = df["date"].max()
    next_day = last + pd.Timedelta(days=1)
    html = TEMPLATE.format(
        last_date=f"{last:%d/%m/%Y}", next_date=f"{next_day:%d/%m/%Y}",
        toolbar=toolbar(f"{next_day:%d/%m/%Y}", actions_url),
        latest=prize_table(df.iloc[-1]["prizes"]), db_full=escape(df.iloc[-1]["prizes"][0]),
        period=f"{df['date'].min():%d/%m/%Y} – {last:%d/%m/%Y}",
        n=len(df), generated=datetime.now(VN_TZ).strftime("%d/%m/%Y %H:%M (giờ VN)"),
        cards=cards, charts=charts_html, stats=stats_html,
        kep_tbl=table(kep_tbl, "compact"), nhay_tbl=table(nhay_tbl, "compact"),
        recent=table(recent_tbl, "recent"),
        suggest=" · ".join(f"{TARGET_SHORT[t]} {k} {_unit(t)}" for t, k in ks.items()),
        tracking=tracking_section(df, ks, tracking_path),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


TEMPLATE = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Thống kê XSMB</title>
<style>
:root {{
  color-scheme: dark;
  --surface: #0b0d14; --card: #141824; --card-2: #1a2030; --border: #262d40;
  --text-primary: #eef1f8; --text-secondary: #a9b1c6; --text-muted: #6f7890;
  --series-1: #5b8cff; --accent: #ff4d5e; --gold: #f5b942; --grid: #262d40;
  --hero-1: #ff4d5e33; --hero-2: #f5b94226; --nav: #0b0d14cc; --shadow: 0 8px 30px #0006;
  --c-loto: #f5b942; --c-de: #ff4d5e; --c-kep: #b07cff; --c-cap: #2ed3b7;
}}
@media (prefers-color-scheme: light) {{
  :root:not([data-theme="dark"]) {{
    color-scheme: light;
    --surface: #f4f5f9; --card: #ffffff; --card-2: #f7f8fb; --border: #e3e6ee;
    --text-primary: #10131c; --text-secondary: #4b5368; --text-muted: #7c8499;
    --series-1: #2f6bff; --accent: #e5304a; --gold: #c98a0b; --grid: #e3e6ee;
    --hero-1: #e5304a22; --hero-2: #f5b94233; --nav: #f4f5f9d9; --shadow: 0 6px 24px #1a20301a;
    --c-loto: #d99a10; --c-de: #e5304a; --c-kep: #8b55e8; --c-cap: #10a88f;
  }}
}}
:root[data-theme="light"] {{
  color-scheme: light;
  --surface: #f4f5f9; --card: #ffffff; --card-2: #f7f8fb; --border: #e3e6ee;
  --text-primary: #10131c; --text-secondary: #4b5368; --text-muted: #7c8499;
  --series-1: #2f6bff; --accent: #e5304a; --gold: #c98a0b; --grid: #e3e6ee;
  --hero-1: #e5304a22; --hero-2: #f5b94233; --nav: #f4f5f9d9; --shadow: 0 6px 24px #1a20301a;
  --c-loto: #d99a10; --c-de: #e5304a; --c-kep: #8b55e8; --c-cap: #10a88f;
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{ margin: 0; background: var(--surface); color: var(--text-primary);
  font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 1120px; margin: 0 auto; padding: 0 16px 64px; }}
h2 {{ font-size: 20px; margin: 0 0 14px; display: flex; align-items: center; gap: 10px; }}
h2::before {{ content: ""; width: 4px; height: 20px; border-radius: 2px;
  background: linear-gradient(var(--accent), var(--gold)); }}
h3 {{ font-size: 15px; margin: 0 0 10px; }}
h4 {{ font-size: 13px; margin: 14px 0 6px; color: var(--text-secondary); }}
section.block {{ scroll-margin-top: 72px; padding-top: 36px; }}
.meta {{ color: var(--text-secondary); margin: 0; }}
a {{ color: var(--series-1); }}

/* Banner */
.hero {{ position: relative; overflow: hidden; border-bottom: 1px solid var(--border);
  background: radial-gradient(600px 300px at 10% 0%, var(--hero-1), transparent 70%),
              radial-gradient(500px 300px at 90% 20%, var(--hero-2), transparent 70%), var(--surface); }}
.hero-in {{ max-width: 1120px; margin: 0 auto; padding: 32px 16px 24px; display: grid; gap: 20px;
  grid-template-columns: minmax(0, 1fr) auto; align-items: end; }}
.hero h1 {{ font-size: clamp(26px, 4vw, 38px); line-height: 1.1; margin: 0 0 8px; letter-spacing: -.02em; }}
.hero h1 span {{ background: linear-gradient(90deg, var(--accent), var(--gold));
  -webkit-background-clip: text; background-clip: text; color: transparent; }}
.spot {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 14px 18px;
  box-shadow: var(--shadow); text-align: right; }}
.spot .label {{ color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }}
.spot .db {{ font: 800 34px/1.1 ui-monospace, Menlo, monospace; letter-spacing: .08em;
  background: linear-gradient(90deg, var(--accent), var(--gold)); -webkit-background-clip: text;
  background-clip: text; color: transparent; }}
.warn {{ border: 1px solid var(--border); border-left: 3px solid var(--accent); background: var(--card);
  padding: 10px 14px; margin: 0; color: var(--text-secondary); border-radius: 10px; font-size: 13px; }}
.hero .warn {{ grid-column: 1 / -1; }}

/* Thanh điều hướng dính */
nav.jump {{ position: sticky; top: 0; z-index: 20; background: var(--nav);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-bottom: 1px solid var(--border); }}
nav.jump .in {{ max-width: 1120px; margin: 0 auto; padding: 10px 16px; display: flex; gap: 6px;
  align-items: center; overflow-x: auto; scrollbar-width: none; }}
nav.jump .in::-webkit-scrollbar {{ display: none; }}
nav.jump a {{ flex: none; text-decoration: none; color: var(--text-secondary); font-weight: 600; font-size: 13px;
  padding: 7px 12px; border-radius: 999px; border: 1px solid transparent; transition: .15s; }}
nav.jump a:hover {{ color: var(--text-primary); background: var(--card); }}
nav.jump a.on {{ color: #fff; background: linear-gradient(90deg, var(--accent), #ff7a45);
  box-shadow: 0 4px 14px #ff4d5e55; }}
nav.jump .sp {{ flex: 1; }}
#theme {{ flex: none; border: 1px solid var(--border); background: var(--card); color: var(--text-primary);
  border-radius: 999px; width: 34px; height: 34px; cursor: pointer; font-size: 15px; }}
#top {{ position: fixed; right: 18px; bottom: 18px; z-index: 30; width: 46px; height: 46px; border-radius: 50%;
  border: none; cursor: pointer; color: #fff; font-size: 20px; box-shadow: 0 8px 24px #ff4d5e66;
  background: linear-gradient(135deg, var(--accent), var(--gold)); opacity: 0; pointer-events: none;
  transform: translateY(10px); transition: .2s; }}
#top.show {{ opacity: 1; pointer-events: auto; transform: none; }}

/* Thẻ */
.grid2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(300px, 100%), 1fr)); gap: 16px; }}
.cards {{ grid-template-columns: repeat(auto-fit, minmax(min(420px, 100%), 1fr)); }}
.card {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px;
  padding: 18px; margin: 0; min-width: 0; box-shadow: var(--shadow); }}
figcaption {{ font-weight: 600; margin-bottom: 8px; }}
.wide {{ grid-column: 1 / -1; }}
.pick {{ --c: var(--series-1); position: relative; overflow: hidden; }}
.pick::before {{ content: ""; position: absolute; inset: 0 0 auto; height: 3px;
  background: linear-gradient(90deg, var(--c), transparent); }}
.t-loto {{ --c: var(--c-loto); }} .t-de {{ --c: var(--c-de); }}
.t-kep {{ --c: var(--c-kep); }} .t-cap {{ --c: var(--c-cap); }}
.pick-head {{ display: flex; align-items: center; justify-content: space-between; }}
.pick-head h3 {{ font-size: 18px; margin: 0; }}
.badge {{ font-size: 12px; font-weight: 700; color: var(--c); border: 1px solid var(--c);
  border-radius: 999px; padding: 2px 10px; }}
.pick .sub {{ color: var(--text-muted); font-size: 12px; margin: 2px 0 14px; }}
.balls {{ display: flex; flex-wrap: wrap; gap: 10px; }}
.ball {{ width: 52px; height: 52px; border-radius: 50%; display: grid; place-items: center;
  font: 800 20px/1 ui-monospace, Menlo, monospace; color: #fff; text-shadow: 0 1px 2px #0006;
  background: radial-gradient(circle at 30% 22%, #ffffff59, transparent 32%),
              radial-gradient(circle at 35% 30%, var(--c), color-mix(in srgb, var(--c) 55%, #000) 75%);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--c) 40%, transparent), inset 0 -4px 8px #0004; }}
.ball.pair {{ width: auto; padding: 0 20px; border-radius: 999px; }}
.bt-line {{ display: flex; align-items: baseline; gap: 8px; margin: 16px 0 4px; padding: 10px 12px;
  border-radius: 10px; background: var(--card-2); color: var(--text-muted); font-size: 12px; }}
.bt-line b {{ color: var(--text-primary); font-size: 16px; }}
details {{ margin-top: 8px; }}
summary {{ cursor: pointer; color: var(--text-secondary); font-size: 13px; padding: 4px 0; }}
summary:hover {{ color: var(--text-primary); }}

/* Bảng */
.table-wrap {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); }}
th {{ color: var(--text-muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
tbody tr:hover td {{ background: var(--card-2); }}
table.recent td:last-child {{ font-family: ui-monospace, Menlo, monospace; font-size: 12px; }}
table.track td {{ font-family: ui-monospace, Menlo, monospace; font-size: 12px; white-space: nowrap; }}
.got {{ color: var(--accent); }}
.tag {{ font: 11px system-ui, sans-serif; color: var(--text-muted); border: 1px solid var(--border);
  border-radius: 4px; padding: 0 4px; }}
.tag.ok {{ color: var(--accent); border-color: var(--accent); }}
.prizes td:first-child {{ color: var(--text-secondary); width: 80px; }}
.prizes td:last-child {{ font: 600 16px ui-monospace, Menlo, monospace; word-spacing: 10px; }}
.prizes tr.db td:last-child {{ color: var(--accent); font-size: 24px; font-weight: 800; }}

/* Số liệu */
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(170px, 100%), 1fr)); gap: 12px; }}
.stat {{ background: var(--card-2); border-radius: 10px; padding: 12px; }}
.stat .label {{ color: var(--text-secondary); font-size: 12px; }}
.stat .value {{ font-size: 26px; font-weight: 750; }}
.stat .sub {{ color: var(--text-muted); font-size: 12px; }}

/* Biểu đồ */
.chart {{ width: 100%; height: auto; display: block; }}
.chart .bar {{ fill: var(--series-1); }}
.chart .bar.hl {{ fill: var(--accent); }}
.chart .grid {{ stroke: var(--grid); stroke-width: 1; }}
.chart .tick {{ fill: var(--text-muted); font-size: 11px; }}
.chart .hitbox {{ fill: transparent; }}
.chart .hit:hover .bar {{ opacity: .75; }}
.legend {{ color: var(--text-secondary); font-size: 13px; margin: 0 0 12px; }}
.legend i {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px;
  margin: 0 4px 0 12px; vertical-align: -1px; }}
#tip {{ position: fixed; pointer-events: none; background: var(--text-primary); color: var(--card);
  padding: 4px 8px; border-radius: 4px; font-size: 12px; display: none; z-index: 40; }}

/* Nút */
.toolbar {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin: 14px 0 0; }}
.toolbar button {{ font-family: inherit; font-size: 14px; font-weight: 700; padding: 10px 16px; border-radius: 10px;
  cursor: pointer; border: 1px solid var(--border); background: var(--card); color: var(--text-primary); transition: .15s; }}
.toolbar button:hover {{ transform: translateY(-1px); }}
.toolbar button.primary {{ border: none; color: #fff; background: linear-gradient(90deg, var(--accent), #ff7a45);
  box-shadow: 0 6px 18px #ff4d5e55; }}
.toolbar button:disabled {{ opacity: .5; cursor: progress; transform: none; }}
#status {{ color: var(--text-secondary); font-size: 13px; }}
#status.error {{ color: var(--accent); }}
.toolbar .note {{ color: var(--text-secondary); }}

@media (max-width: 640px) {{
  .hero-in {{ grid-template-columns: 1fr; }}
  .spot {{ text-align: left; }}
  .ball {{ width: 46px; height: 46px; font-size: 18px; }}
}}
</style>
<script>try {{ const t = localStorage.getItem('theme'); if (t) document.documentElement.dataset.theme = t; }} catch (_) {{}}</script>
</head>
<body>
<header class="hero" id="dau-trang"><div class="hero-in">
  <div>
    <h1>Thống kê &amp; dự đoán <span>XSMB</span></h1>
    <p class="meta">{n} kỳ quay ({period}) · gợi ý: {suggest}</p>
    <p class="meta" style="font-size:12px">Tạo lúc {generated}</p>
    {toolbar}
  </div>
  <div class="spot">
    <div class="label">Đặc biệt {last_date}</div>
    <div class="db">{db_full}</div>
  </div>
  <div class="warn">Xổ số là ngẫu nhiên — mỗi kỳ quay độc lập. Các "dự đoán" chỉ là xếp hạng theo thống kê
  quá khứ; hãy so sánh với <b>xác suất chọn bừa</b>. Cột <b>p (Holm)</b> &lt; 0,05 mới là dấu hiệu đáng chú ý.</div>
</div></header>

<nav class="jump" aria-label="Đi tới mục"><div class="in">
  <a href="#goi-y">Gợi ý</a>
  <a href="#ket-qua">Kết quả</a>
  <a href="#theo-doi">Theo dõi</a>
  <a href="#kep">Kép &amp; ĐB</a>
  <a href="#bieu-do">Biểu đồ</a>
  <a href="#gan-day">30 kỳ</a>
  <span class="sp"></span>
  <button id="theme" type="button" title="Đổi giao diện sáng/tối" aria-label="Đổi giao diện sáng/tối">◐</button>
</div></nav>

<main>
<section class="block" id="goi-y">
  <h2>Gợi ý kỳ {next_date}</h2>
  <div class="grid2 cards">{cards}</div>
</section>

<section class="block" id="ket-qua">
  <h2>Kết quả mới nhất · {last_date}</h2>
  <div class="card table-wrap">{latest}</div>
</section>

<section class="block" id="theo-doi">
  <h2>Theo dõi dự đoán thực tế</h2>
  {tracking}
</section>

<section class="block" id="kep">
  <h2>Thống kê kép &amp; đặc biệt</h2>
  <div class="card stats">{stats}</div>
  <div class="grid2" style="margin-top:16px">
    <section class="card"><h3>10 lần ĐB về kép gần nhất</h3>{kep_tbl}</section>
    <section class="card"><h3>Lô về nhiều nháy (30 kỳ)</h3>{nhay_tbl}</section>
  </div>
</section>

<section class="block" id="bieu-do">
  <h2>Biểu đồ</h2>
  <p class="legend"><i style="background:var(--series-1)"></i>Số lần / số kỳ
  <i style="background:var(--accent)"></i>Số được gợi ý kỳ tới</p>
  <div class="grid2">{charts}</div>
</section>

<section class="block" id="gan-day">
  <h2>30 kỳ gần nhất</h2>
  <div class="card table-wrap">{recent}</div>
</section>
</main>
<button id="top" type="button" title="Lên đầu trang" aria-label="Lên đầu trang">↑</button>
<div id="tip"></div>
<script>
// Điều hướng: tô sáng mục đang xem, hiện nút lên đầu trang
const links = [...document.querySelectorAll('nav.jump a')];
const spy = new IntersectionObserver(entries => {{
  entries.forEach(e => {{
    if (!e.isIntersecting) return;
    links.forEach(a => a.classList.toggle('on', a.getAttribute('href') === '#' + e.target.id));
    const on = links.find(a => a.classList.contains('on'));
    if (on) on.scrollIntoView({{ block: 'nearest', inline: 'nearest' }});
  }});
}}, {{ rootMargin: '-80px 0px -60% 0px' }});
document.querySelectorAll('section.block').forEach(s => spy.observe(s));
const topBtn = document.getElementById('top');
addEventListener('scroll', () => topBtn.classList.toggle('show', scrollY > 600), {{ passive: true }});
topBtn.addEventListener('click', () => scrollTo({{ top: 0, behavior: 'smooth' }}));

// Sáng/tối: nhớ lựa chọn trên trình duyệt này
const root = document.documentElement;
document.getElementById('theme').addEventListener('click', () => {{
  const dark = root.dataset.theme ? root.dataset.theme === 'dark'
    : !matchMedia('(prefers-color-scheme: light)').matches;
  root.dataset.theme = dark ? 'light' : 'dark';
  try {{ localStorage.setItem('theme', root.dataset.theme); }} catch (_) {{}}
}});

const tip = document.getElementById('tip');
document.querySelectorAll('.hit').forEach(g => {{
  g.addEventListener('mousemove', e => {{
    tip.textContent = g.dataset.tip; tip.style.display = 'block';
    tip.style.left = Math.min(e.clientX + 12, innerWidth - tip.offsetWidth - 8) + 'px';
    tip.style.top = (e.clientY - 32) + 'px';
  }});
  g.addEventListener('mouseleave', () => tip.style.display = 'none');
}});

// Các nút cần server: python -m src.server
const status = document.getElementById('status');
const buttons = document.querySelectorAll('.toolbar button');
if (status && location.protocol === 'file:') {{
  buttons.forEach(b => b.disabled = true);
  status.textContent = 'Mở qua server để dùng nút: python -m src.server → http://localhost:8000';
}}
buttons.forEach(btn => btn.addEventListener('click', async () => {{
  buttons.forEach(b => b.disabled = true);
  status.className = '';
  status.textContent = btn.id === 'btn-update' ? 'Đang tải kết quả…' : 'Đang tính dự đoán và backtest…';
  try {{
    let res;
    try {{
      res = await fetch(btn.dataset.api, {{ method: 'POST' }});
    }} catch (_) {{
      throw new Error('Không kết nối được server. Mở terminal, chạy "python -m src.server" '
        + 'trong thư mục xoso-prediction rồi tải lại trang này.');
    }}
    const data = (res.headers.get('content-type') || '').includes('json') ? await res.json() : null;
    if (!data) throw new Error('Trang này không được mở qua server của project. '
      + 'Hãy chạy "python -m src.server" và mở http://localhost:8000.');
    if (!res.ok) throw new Error(data.error || 'Server báo lỗi (mã ' + res.status + ').');
    status.textContent = data.message + ' Đang tải lại trang…';
    setTimeout(() => location.reload(), 800);
  }} catch (e) {{
    status.className = 'error';
    status.textContent = 'Lỗi: ' + e.message;
    buttons.forEach(b => b.disabled = false);
  }}
}}));
</script>
</body></html>
"""
