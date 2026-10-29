"""Sinh báo cáo HTML tự chứa (SVG inline, không phụ thuộc thư viện ngoài)."""
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd

from . import analysis
from .crawler import VN_TZ
from .predict import TARGET_NAMES, kep_outlook

REPORT_FILE = Path(__file__).resolve().parent.parent / "reports" / "report.html"

STRATEGY_NAMES = {"hot": "Hot (ra nhiều 30 kỳ)", "gan": "Gan (lâu chưa ra)",
                  "combo": "Kết hợp", "random": "Ngẫu nhiên", "ly_thuyet": "Xác suất lý thuyết"}


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


def toolbar(next_date: str, k: int, actions_url: str | None) -> str:
    """Thanh nút. actions_url != None: trang tĩnh trên GitHub Pages, thay nút bằng link Run workflow."""
    if actions_url is not None:
        link = (f' Cập nhật ngay: bấm <a href="{escape(actions_url)}" target="_blank" rel="noopener">'
                f'Run workflow trên GitHub</a>.' if actions_url else "")
        return (f'<div class="toolbar"><span class="note">Trang tự cập nhật mỗi tối khoảng 18h40 '
                f'và 20h30 (giờ VN).{link}</span></div>')
    return f"""<div class="toolbar">
  <button id="btn-update" data-api="/api/update">⟳ Tải kết quả mới nhất</button>
  <button id="btn-predict" class="primary" data-api="/api/predict">Dự đoán kỳ {next_date}</button>
  <label>Số gợi ý <input id="k" type="number" min="1" max="20" value="{k}"></label>
  <span id="status"></span>
</div>"""


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _prediction_card(target: str, r: dict, k: int) -> str:
    pred = r["predict"].rename(columns={"so": "Số", "diem": "Điểm", "ra_30_ky": "Ra 30 kỳ",
                                        "ra_tong": "Ra tổng", "gan": "Gan", "gan_max": "Gan max"})
    chips = "".join(f'<span class="chip">{s}</span>' for s in pred["Số"])
    bt = r["backtest"]
    bt_rows = pd.DataFrame({"Chiến lược": [STRATEGY_NAMES[s] for s in bt.index],
                            f"Tỉ lệ trúng ≥1/{k} số": [_pct(v) for v in bt.values]})
    return (f'<section class="card"><h3>{escape(TARGET_NAMES[target])}</h3>'
            f'<div class="chips">{chips}</div>'
            f'<details><summary>Chi tiết điểm</summary>{table(pred)}</details>'
            f'<h4>Backtest</h4>{table(bt_rows, "compact")}</section>')


def write_report(df: pd.DataFrame, results: dict, k: int, path: Path = REPORT_FILE,
                 actions_url: str | None = None) -> Path:
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

    cards = "".join(_prediction_card(t, r, k) for t, r in results.items())
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
        toolbar=toolbar(f"{next_day:%d/%m/%Y}", k, actions_url),
        latest=prize_table(df.iloc[-1]["prizes"]),
        period=f"{df['date'].min():%d/%m/%Y} – {last:%d/%m/%Y}",
        n=len(df), k=k, generated=datetime.now(VN_TZ).strftime("%d/%m/%Y %H:%M (giờ VN)"),
        cards=cards, charts=charts_html, stats=stats_html,
        kep_tbl=table(kep_tbl, "compact"), nhay_tbl=table(nhay_tbl, "compact"),
        recent=table(recent_tbl, "recent"),
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
  color-scheme: light;
  --surface: #f6f6f4; --card: #fcfcfb; --border: #e3e2de;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #7a7974;
  --series-1: #2a78d6; --accent: #eb6834; --grid: #e3e2de;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --surface: #121211; --card: #1a1a19; --border: #2e2e2c;
    --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #8f8e86;
    --series-1: #3987e5; --accent: #d95926; --grid: #2e2e2c;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --surface: #121211; --card: #1a1a19; --border: #2e2e2c;
  --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #8f8e86;
  --series-1: #3987e5; --accent: #d95926; --grid: #2e2e2c;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--surface); color: var(--text-primary);
  font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }}
h1 {{ font-size: 24px; margin: 0 0 4px; }}
h2 {{ font-size: 18px; margin: 32px 0 12px; }}
h3 {{ font-size: 15px; margin: 0 0 10px; }}
h4 {{ font-size: 13px; margin: 14px 0 6px; color: var(--text-secondary); }}
.meta {{ color: var(--text-secondary); margin: 0; }}
.warn {{ border-left: 3px solid var(--accent); background: var(--card); padding: 10px 14px;
  margin: 16px 0; color: var(--text-secondary); border-radius: 4px; }}
.grid2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(300px, 100%), 1fr)); gap: 16px; }}
.card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
  padding: 16px; margin: 0; min-width: 0; }}
figcaption {{ font-weight: 600; margin-bottom: 8px; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.chip {{ font: 600 20px/1 ui-monospace, Menlo, monospace; padding: 8px 12px; border-radius: 6px;
  border: 1px solid var(--border); background: var(--surface); }}
details {{ margin-top: 10px; }}
summary {{ cursor: pointer; color: var(--text-secondary); }}
.table-wrap {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }}
th, td {{ text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--border); }}
th {{ color: var(--text-secondary); font-weight: 600; }}
table.recent td:last-child {{ font-family: ui-monospace, Menlo, monospace; font-size: 12px; }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(170px, 100%), 1fr)); gap: 12px; }}
.stat .label {{ color: var(--text-secondary); font-size: 13px; }}
.stat .value {{ font-size: 26px; font-weight: 650; }}
.stat .sub {{ color: var(--text-muted); font-size: 12px; }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart .bar {{ fill: var(--series-1); }}
.chart .bar.hl {{ fill: var(--accent); }}
.chart .grid {{ stroke: var(--grid); stroke-width: 1; }}
.chart .tick {{ fill: var(--text-muted); font-size: 11px; }}
.wide {{ grid-column: 1 / -1; }}
.toolbar {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin: 16px 0; }}
.toolbar button {{ font-family: inherit; font-size: 14px; font-weight: 600; padding: 10px 16px; border-radius: 6px; cursor: pointer;
  border: 1px solid var(--border); background: var(--card); color: var(--text-primary); }}
.toolbar button.primary {{ background: var(--series-1); border-color: var(--series-1); color: #fff; }}
.toolbar button:disabled {{ opacity: .5; cursor: progress; }}
.toolbar label {{ color: var(--text-secondary); }}
.toolbar input {{ width: 52px; padding: 8px; border-radius: 6px; border: 1px solid var(--border);
  background: var(--card); color: var(--text-primary); font: inherit; }}
#status {{ color: var(--text-secondary); font-size: 13px; }}
.toolbar .note {{ color: var(--text-secondary); }}
a {{ color: var(--series-1); }}
#status.error {{ color: var(--accent); }}
.prizes td:first-child {{ color: var(--text-secondary); width: 80px; }}
.prizes td:last-child {{ font: 600 16px ui-monospace, Menlo, monospace; word-spacing: 10px; }}
.prizes tr.db td:last-child {{ color: var(--accent); font-size: 22px; }}
.chart .hitbox {{ fill: transparent; }}
.chart .hit:hover .bar {{ opacity: .75; }}
.legend {{ color: var(--text-secondary); font-size: 13px; margin: 0 0 12px; }}
.legend i {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px;
  margin: 0 4px 0 12px; vertical-align: -1px; }}
#tip {{ position: fixed; pointer-events: none; background: var(--text-primary); color: var(--card);
  padding: 4px 8px; border-radius: 4px; font-size: 12px; display: none; z-index: 10; }}
</style></head>
<body><main>
<h1>Thống kê &amp; dự đoán XSMB</h1>
<p class="meta">{n} kỳ quay ({period}) · gợi ý {k} số mỗi loại · tạo lúc {generated}</p>
<div class="warn">Xổ số là ngẫu nhiên — mỗi kỳ quay độc lập. Các "dự đoán" dưới đây chỉ là xếp hạng
theo thống kê quá khứ; hãy so sánh dòng backtest với <b>xác suất lý thuyết</b> để thấy chúng không
tốt hơn chọn bừa một cách có ý nghĩa.</div>

{toolbar}

<h2>Kết quả mới nhất · {last_date}</h2>
<div class="card table-wrap">{latest}</div>

<h2>Gợi ý kỳ {next_date}</h2>
<div class="grid2">{cards}</div>

<h2>Thống kê kép &amp; đặc biệt</h2>
<div class="card stats">{stats}</div>
<div class="grid2" style="margin-top:16px">
  <section class="card"><h3>10 lần ĐB về kép gần nhất</h3>{kep_tbl}</section>
  <section class="card"><h3>Lô về nhiều nháy (30 kỳ)</h3>{nhay_tbl}</section>
</div>

<h2>Biểu đồ</h2>
<p class="legend"><i style="background:var(--series-1)"></i>Số lần / số kỳ
<i style="background:var(--accent)"></i>Số được gợi ý kỳ tới</p>
<div class="grid2">{charts}</div>

<h2>30 kỳ gần nhất</h2>
<div class="card table-wrap">{recent}</div>
</main>
<div id="tip"></div>
<script>
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
    const k = document.getElementById('k').value;
    let res;
    try {{
      res = await fetch(btn.dataset.api + '?k=' + encodeURIComponent(k), {{ method: 'POST' }});
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
