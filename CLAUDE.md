# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Project phân tích thống kê / "dự đoán" kết quả xổ số miền Bắc (XSMB). Project mang tính học tập: các kỳ quay độc lập với nhau, và backtest dùng để chứng minh không chiến lược nào hơn ngẫu nhiên. Giữ đúng tinh thần này trong mọi nội dung hiển thị cho người dùng. Comment, docstring, CLI help, commit message và toàn bộ chuỗi giao diện đều viết bằng **tiếng Việt**, hãy viết theo đúng như vậy. `HUONG_DAN.md` là hướng dẫn sử dụng chi tiết và giải thích thuật toán. Khi thay đổi hành vi, tùy chọn hoặc số liệu backtest thì cập nhật cả `HUONG_DAN.md` lẫn `README.md`.

## Lệnh thường dùng

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt          # thư viện khi chạy chỉ gồm pandas, numpy, scipy

python -m src.crawler                        # tải các kỳ mới (cộng dồn); --years N để tải bù kỳ cũ
python -m src.predict                        # thống kê + gợi ý + backtest mọi loại; đồng thời ghi vào sổ dự đoán
python -m src.predict --target de --k 5 --no-record
python -m src.predict --report               # -> reports/report.html
python -m src.predict --site site            # trang tĩnh cho GitHub Pages (CI chạy lệnh này)
python -m src.tracking [--strategy combo] [--last 15]   # chấm điểm sổ dự đoán thực tế
python -m src.server [--port 8000]           # trang local có nút "tải kết quả" / "dự đoán"

python -m pytest                             # chạy toàn bộ test
python -m pytest tests/test_predict.py::test_backtest_rates_in_range   # chạy một test
```

Test dùng dữ liệu giả lập từ `generate_sample()`, không cần mạng. Khi chưa có `data/raw/results.csv`, `predict` cũng tự dùng dữ liệu ngẫu nhiên mẫu.

## Kiến trúc

Luồng xử lý: `crawler` → `data/raw/results.csv` → `data_loader` → `analysis` (ma trận theo từng loại) → `predict` (chiến lược + backtest walk-forward) → `tracking` (sổ dự đoán) + `report` (HTML). `server` và GitHub workflow chỉ là lớp gọi mỏng tới `predict.build_report()` / `predict.main()`.

- **Định dạng dữ liệu**: `results.csv` gồm `date,numbers`, trong đó `numbers` là 27 số đầy đủ theo thứ tự giải, số đầu tiên luôn là giải Đặc biệt (ĐB). `load_results()` tạo thêm các cột `prizes` (chuỗi), `numbers` (2 số cuối, kiểu int) và `db`.
- **Loại dự đoán** (`analysis.TARGETS`):
  - `loto`: bất kỳ giải nào trong 27 giải, tập số 0–99.
  - `de`: chỉ giải ĐB.
  - `kep`: lô kép 00..99, tập 10 số.
  - `cap`: cặp lộn như 59-95, tập 45 giá trị `CAP`. Mỗi cặp ghi bằng số nhỏ hơn và không gồm số kép.
  - `dekep`: chỉ dùng cho thống kê.

  Mọi bước phía sau đều làm việc trên `analysis.matrix(df, target)`, là ma trận đếm kích thước `(số kỳ × len(universe(target)))`. Muốn thêm loại mới thì sửa `universe`/`draws`/`label` và `predict.theoretical`.
- **Chiến lược** (`predict.py`): mỗi hàm `score_*(m)` nhận ma trận lịch sử và trả về một điểm cho mỗi số trong tập. `BASE` chứa các chiến lược cơ sở. `ensemble` (lấy trung bình thứ hạng kiểu Borda) và `hedge` (trọng số nhân trực tuyến trên `BASE`, thưởng theo số lượt trúng trong top-`HEDGE_K`) dùng để kết hợp chúng. `random` là nhóm đối chứng. Chiến lược mới cần được đăng ký vào `BASE`/`STRATEGIES` và thêm tên hiển thị vào `report.STRATEGY_NAMES`.
- **`evaluate()`** là vòng lặp cốt lõi. Hàm chạy walk-forward bắt đầu từ `WARMUP`, nên bước *i* chỉ thấy `m[:i]`. Tỉ lệ trúng của mỗi chiến lược được kiểm định so với `theoretical(target, k)` bằng binomial test một phía, kèm hiệu chỉnh Holm. Vòng lặp cuối (dùng toàn bộ dữ liệu) sinh ra `picks` cho kỳ tới của mọi chiến lược, nhờ vậy không phải tính lại trọng số hedge. Không được để lọt dữ liệu tương lai (look-ahead).
- **Số lượng gợi ý** lấy từ `SUGGEST_K` (`loto 3, de 10, kep 2, cap 1`). Phần gợi ý hiển thị của hệ thống dùng chiến lược `combo` (`tracking.SYSTEM_STRATEGY`).
- **Sổ dự đoán** (`data/predictions.csv`):
  - Mỗi lần chạy `predict` (trừ khi có `--no-record`), `tracking.record()` ghi thêm số gợi ý kỳ tới cho mọi bộ (loại, chiến lược, k).
  - Mỗi khóa chỉ giữ bản ghi đầu tiên.
  - Từ 18h giờ Việt Nam ngày quay thì không ghi thêm cho kỳ đó nữa (`DRAW_HOUR`, `crawler.VN_TZ`).

  Đây là thước đo trung thực ngoài mẫu, nên không được sửa các dòng đã có.
- **Crawler**: dùng endpoint JSON của rongbachkim.com (`API_URL`, tối đa 300 kỳ mỗi request). `update()` không bao giờ xóa dữ liệu đã có. Kỳ chưa đủ 27 số (đang quay) sẽ được bỏ qua để lần sau tải lại.
- **Báo cáo**: `report.py` tạo một file HTML độc lập từ chuỗi `TEMPLATE`, biểu đồ là SVG inline. Không dùng framework JS hay tài nguyên ngoài, nên mở offline được. Server local thêm các nút gửi POST tới `/api/update` và `/api/predict`. Bản `--site` không có nút mà thay bằng link tới workflow trên GitHub Actions (`actions_url()`).

## Triển khai / git

`.github/workflows/daily.yml` chạy mỗi ngày lúc 18h40 và 20h30 giờ Việt Nam. Workflow chạy crawler, rồi `predict --site site`, commit các thay đổi trong `data/` dưới tên `github-actions[bot]` và đăng `site/` lên GitHub Pages. Vì CI push lên `main` hằng ngày nên **luôn `git pull` trước khi commit hoặc push**. Các file sinh ra (`reports/`, `site/`) nằm trong gitignore, còn `data/` thì được commit.
