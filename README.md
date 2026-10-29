# Xổ Số Prediction

Project phân tích thống kê kết quả xổ số (mặc định: XSMB – 2 số cuối "lô").

> ⚠️ **Lưu ý:** Xổ số là ngẫu nhiên — mỗi kỳ quay độc lập với các kỳ trước.
> Không mô hình nào dự đoán được kết quả tốt hơn ngẫu nhiên. Project này dùng
> để học phân tích dữ liệu / thống kê, **không** phải công cụ kiếm tiền.

📖 Hướng dẫn chi tiết và giải thích thuật toán: [HUONG_DAN.md](HUONG_DAN.md)

## Cấu trúc

```
xoso-prediction/
├── .github/workflows/daily.yml  # GitHub Actions: tự cập nhật + đăng GitHub Pages mỗi tối
├── data/raw/results.csv  # date, numbers (27 số đầy đủ, số đầu tiên là giải ĐB)
├── data/predictions.csv  # sổ dự đoán đã ghi trước mỗi kỳ (python -m src.tracking để xem)
├── reports/report.html   # báo cáo HTML khi chạy trên máy (sinh ra bằng --report)
├── src/
│   ├── crawler.py        # Tải kết quả XSMB từ rongbachkim.com
│   ├── data_loader.py    # Đọc dữ liệu (cột numbers = 27 lô, db = 2 số cuối ĐB)
│   ├── analysis.py       # Tần suất, gan, gan max, đầu/đuôi, kép, nháy, chi-square
│   ├── predict.py        # 8 chiến lược + kết hợp (Borda, Hedge) + backtest có kiểm định
│   ├── tracking.py       # Sổ theo dõi: ghi dự đoán trước giờ quay, chấm điểm khi có kết quả
│   ├── report.py         # Báo cáo HTML (SVG inline, mở offline được)
│   └── server.py         # Web server local cho các nút trên trang
├── requirements.txt      # thư viện cần để chạy
└── requirements-dev.txt  # thêm pytest, jupyter để phát triển
```

## Chạy tự động trên GitHub (không cần máy cá nhân)

GitHub Actions tự tải kết quả và đăng trang dự đoán lên GitHub Pages mỗi tối
(~18h40 và 20h30 giờ VN). Cách cài đặt từng bước: [HUONG_DAN.md, mục 11](HUONG_DAN.md#11-chạy-tự-động-trên-github-không-cần-máy-cá-nhân).

## Loại dự đoán (`--target`)

| target  | Ý nghĩa |
|---------|---------|
| `de`    | 2 số cuối giải Đặc biệt |
| `loto`  | 2 số cuối của bất kỳ giải nào (27 giải) |
| `kep`   | Lô kép (00, 11, …, 99) về ở bất kỳ giải nào |
| `cap`   | Cặp lô lộn (59-95, …): ít nhất 1 trong 2 số về ở bất kỳ giải nào |

Số gợi ý mặc định: **Loto 3 · Đề 10 · Lô kép 2 · Cặp lộn 1 cặp** (sửa `SUGGEST_K` trong `src/predict.py`).
| `all`   | Tất cả (mặc định) |

Backtest chạy walk-forward (chỉ dùng dữ liệu trước mỗi kỳ để chọn số cho kỳ đó)
và in kèm **xác suất lý thuyết** khi chọn ngẫu nhiên — đây là thước đo để biết
một chiến lược có thật sự hơn ngẫu nhiên hay không.

## Bắt đầu

```bash
cd ~/xoso-prediction
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# 1. Tải 5 năm kết quả (lần đầu), các lần sau chỉ tải ngày mới; không xoá dữ liệu cũ
python -m src.crawler            # thêm --years 10 để tải bù thêm kỳ cũ

# Cách nhanh nhất: mở trang web có nút "Tải kết quả mới nhất" và "Dự đoán kỳ …"
python -m src.server          # tự mở http://localhost:8000

# Hoặc dùng dòng lệnh:
# 2. Thống kê + gợi ý + backtest, xuất báo cáo HTML
python -m src.predict --report
open reports/report.html

# Chạy test
python -m pytest
```

Nếu chưa có dữ liệu, `predict.py` sẽ tự sinh dữ liệu ngẫu nhiên mẫu để chạy thử.
