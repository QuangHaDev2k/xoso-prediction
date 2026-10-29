# Hướng dẫn sử dụng & giải thích thuật toán

> ⚠️ Xổ số là ngẫu nhiên: mỗi kỳ quay độc lập với các kỳ trước. Hệ thống này chỉ
> **thống kê dữ liệu quá khứ** và **xếp hạng** các con số theo một số tiêu chí.
> Phần [Backtest](#5-backtest--kiểm-chứng-thuật-toán) cho thấy các xếp hạng này
> không trúng nhiều hơn chọn ngẫu nhiên. Đừng dùng kết quả để đặt cược.

## Mục lục

1. [Cài đặt lần đầu](#1-cài-đặt-lần-đầu)
2. [Sử dụng hằng ngày](#2-sử-dụng-hằng-ngày)
3. [Các tùy chọn dòng lệnh](#3-các-tùy-chọn-dòng-lệnh)
4. [Thuật toán dự đoán](#4-thuật-toán-dự-đoán)
5. [Backtest — kiểm chứng thuật toán](#5-backtest--kiểm-chứng-thuật-toán)
6. [Các chỉ số thống kê khác](#6-các-chỉ-số-thống-kê-khác)
7. [Đọc kết quả trên terminal và báo cáo HTML](#7-đọc-kết-quả-trên-terminal-và-báo-cáo-html)
8. [Dữ liệu](#8-dữ-liệu)
9. [Lỗi thường gặp](#9-lỗi-thường-gặp)
10. [Sử dụng từ Python](#10-sử-dụng-từ-python)
11. [Chạy tự động trên GitHub (không cần máy cá nhân)](#11-chạy-tự-động-trên-github-không-cần-máy-cá-nhân)

---

## 1. Cài đặt lần đầu

Yêu cầu: Python 3.10 trở lên, có kết nối Internet để tải dữ liệu.

```bash
cd ~/xoso-prediction
python3 -m venv .venv              # tạo môi trường Python riêng (đã tạo sẵn thì bỏ qua)
source .venv/bin/activate
pip install -r requirements.txt
```

> Cài thêm công cụ phát triển (pytest, jupyter): `pip install -r requirements-dev.txt`.

Kiểm tra cài đặt:

```bash
pytest          # kết quả mong đợi: 10 passed
```

## 2. Sử dụng hằng ngày

> Không muốn chạy trên máy cá nhân? Xem [mục 11](#11-chạy-tự-động-trên-github-không-cần-máy-cá-nhân):
> GitHub tự cập nhật và đăng trang mỗi tối, bạn chỉ cần mở link.

Xổ số miền Bắc quay lúc 18h15, nên chạy sau khoảng **18h35** để có kết quả mới nhất.

### Cách 1: dùng trang web (khuyên dùng)

```bash
cd ~/xoso-prediction
source .venv/bin/activate
python -m src.server            # tự mở http://localhost:8000; Ctrl+C để tắt
```

Trên trang có thanh công cụ:

| Nút | Tác dụng |
|---|---|
| **⟳ Tải kết quả mới nhất** | Tải các kỳ mới từ rongbachkim.com, cập nhật bảng "Kết quả mới nhất" và tính lại toàn bộ dự đoán |
| **Dự đoán kỳ dd/mm/yyyy** | Tính dự đoán đầy đủ cho kỳ tiếp theo (cả 4 loại: đề, loto, lô kép, ĐB về kép) kèm backtest |
| Ô **Số gợi ý** | Số con số gợi ý mỗi loại (1–20), áp dụng cho cả 2 nút |

Mỗi lần bấm mất vài giây (do chạy backtest), xong trang tự tải lại.
Server chỉ chạy trên máy của bạn (`127.0.0.1`), máy khác trong mạng không truy cập được.
Đổi cổng: `python -m src.server --port 9000`.

> Nếu mở thẳng file `reports/report.html` (không qua server), các nút sẽ bị mờ đi
> vì trình duyệt không thể tự chạy Python.

### Cách 2: dùng dòng lệnh

```bash
cd ~/xoso-prediction
source .venv/bin/activate              # bắt buộc mỗi khi mở terminal mới

python -m src.crawler                  # 1. tải thêm kết quả các ngày mới
python -m src.predict --report         # 2. thống kê, gợi ý, backtest, tạo báo cáo
open reports/report.html               # 3. mở báo cáo trên trình duyệt
```

Lần chạy đầu tiên, `crawler` tải toàn bộ 365 ngày gần nhất. Những lần sau nó chỉ
tải các ngày chưa có trong file và tự xóa các ngày cũ hơn 365 ngày.

## 3. Các tùy chọn dòng lệnh

### `python -m src.crawler`

| Tùy chọn | Mặc định | Ý nghĩa |
|---|---|---|
| `--days N` | 365 | Số ngày lịch tính lùi từ hôm nay. Ví dụ `--days 730` = 2 năm |

> Nếu đổi sang số ngày lớn hơn số ngày đã có, hãy xóa `data/raw/results.csv`
> rồi chạy lại. Chế độ cập nhật tăng dần chỉ lấy các ngày **mới hơn** ngày gần
> nhất trong file, không lấy bù các ngày cũ hơn.

### `python -m src.predict`

| Tùy chọn | Mặc định | Ý nghĩa |
|---|---|---|
| `--target` | `all` | Loại dự đoán: `de`, `loto`, `kep`, `dekep` hoặc `all` |
| `--k N` | 5 | Số lượng con số gợi ý cho mỗi loại |
| `--report` | tắt | Tạo thêm file `reports/report.html` |
| `--site DIR` | tắt | Tạo trang tĩnh `DIR/index.html` không có nút (dùng cho GitHub Pages) |

Ý nghĩa các loại dự đoán:

| `--target` | Tên gọi | Mỗi kỳ được tính là "ra" những số nào |
|---|---|---|
| `de` | Đề / 2 số cuối giải Đặc biệt | 1 số: 2 chữ số cuối của giải ĐB |
| `loto` | Lô tô | 27 số: 2 chữ số cuối của cả 27 giải (ĐB, G1, 2×G2, 6×G3, 4×G4, 6×G5, 3×G6, 4×G7) |
| `kep` | Lô kép | Các số kép (00, 11, 22, …, 99) nằm trong 27 lô ở trên |
| `dekep` | Đặc biệt về kép | 2 số cuối giải ĐB, chỉ khi đó là số kép; nếu không phải kép thì kỳ đó "không ra kép nào" |

Ví dụ:

```bash
python -m src.predict --target de --k 10      # 10 số gợi ý cho đề
python -m src.predict --target kep            # chỉ xem lô kép
python -m src.predict --target all --k 3 --report
```

## 4. Thuật toán dự đoán

### 4.1. Dữ liệu đầu vào: ma trận lịch sử

Với mỗi loại dự đoán, dữ liệu được chuyển thành một **ma trận M**:

- mỗi **dòng** là một kỳ quay, xếp từ cũ đến mới;
- mỗi **cột** là một con số có thể ra (00–99 với `de`/`loto`, hoặc 10 số kép với `kep`/`dekep`);
- `M[kỳ, số]` = số lần con số đó xuất hiện trong kỳ đó (với `loto` có thể là 2, 3 nếu về nhiều nháy).

Từ ma trận này tính ra 3 đại lượng cơ bản cho mỗi con số:

| Đại lượng | Cách tính | Ví dụ |
|---|---|---|
| **Tần suất 30 kỳ** | Tổng số lần xuất hiện trong 30 kỳ gần nhất | Lô 75 về 21 lần trong 30 kỳ |
| **Tần suất tổng** | Tổng số lần xuất hiện trong toàn bộ dữ liệu | Lô 14 về 124 lần trong 360 kỳ |
| **Gan** | Số kỳ liên tiếp **gần nhất** con số chưa xuất hiện. Gan = 0 nghĩa là kỳ vừa rồi có về | Lô 51 gan 15 kỳ |
| **Gan max** | Chuỗi kỳ **dài nhất** trong lịch sử mà con số không xuất hiện | Lô 51 từng gan tối đa 17 kỳ |

> Nếu một số **chưa từng ra** trong toàn bộ dữ liệu, gan = số kỳ của dữ liệu (ví dụ 360).

### 4.2. Bốn chiến lược chấm điểm

Mỗi chiến lược cho mỗi con số một **điểm**. Hệ thống lấy **k số có điểm cao nhất**.
Khi hai số bằng điểm, số nhỏ hơn được xếp trước.

#### a) `hot` — số "nóng"

```
điểm = tần suất 30 kỳ gần nhất
```

Ý tưởng: số đang ra nhiều sẽ còn ra tiếp ("cầu đang chạy").

#### b) `gan` — số "lì"

```
điểm = gan hiện tại
```

Ý tưởng: số lâu chưa ra "đến lúc phải ra" (nuôi lô gan).

#### c) `combo` — kết hợp (chiến lược được dùng cho phần **gợi ý**)

```
điểm = 0.4 × chuẩn_hóa(tần suất 30 kỳ)
     + 0.3 × chuẩn_hóa(tần suất tổng)
     + 0.3 × min(gan / gan_max, 1)
```

- `chuẩn_hóa(x) = (x − min) / (max − min)` đưa giá trị về khoảng 0–1 để các thành phần cộng được với nhau.
- `gan / gan_max` đo con số đang gan **gần mức kỷ lục của chính nó** đến đâu.
  Bằng 1 nghĩa là đang chạm hoặc vượt gan cực đại từng có.

Ví dụ với lô 51 (kỳ 29/10/2026): ra 12 lần/30 kỳ, 110 lần tổng, gan 15 / gan max 17.
Thành phần gan = 15/17 ≈ 0.88, nên điểm cao dù tần suất tổng chỉ ở mức trung bình.

Trọng số 0.4 / 0.3 / 0.3 là **chọn tay**, không được tối ưu từ dữ liệu.
Muốn thử trọng số khác thì sửa hàm `score_combo` trong `src/predict.py`.

#### d) `random` — ngẫu nhiên

```
điểm = số ngẫu nhiên trong [0, 1)
```

Dùng làm **mốc so sánh**: một chiến lược chỉ có giá trị nếu nó trúng nhiều hơn
chiến lược này một cách ổn định. Mỗi lần chạy, kết quả của `random` sẽ hơi khác nhau.

### 4.3. Riêng phần "Đặc biệt về kép"

Ngoài xếp hạng 10 số kép (target `dekep`), hệ thống in thêm:

- **Tỉ lệ ĐB về kép thực tế** = số kỳ ĐB là kép / tổng số kỳ.
- **Tỉ lệ lý thuyết** = 10/100 = **10%** (10 số kép trong 100 số).
- **Số kỳ ĐB chưa về kép** (gan của "kép" nói chung).
- **Số lô kép trung bình mỗi kỳ** (lý thuyết: 27 × 10% = **2,7**).

## 5. Backtest — kiểm chứng thuật toán

### 5.1. Cách làm (walk-forward)

Backtest giả lập việc dùng thuật toán mỗi ngày trong quá khứ, **không nhìn trước tương lai**:

```
for mỗi kỳ i từ kỳ thứ 61 đến kỳ cuối:
    lịch_sử = các kỳ 1 … i−1
    với mỗi chiến lược:
        chọn k số từ lịch_sử
        trúng = (ít nhất 1 trong k số xuất hiện ở kỳ i)
tỉ lệ trúng = số kỳ trúng / số kỳ kiểm tra
```

60 kỳ đầu (`warmup`) chỉ dùng làm lịch sử ban đầu. Với 360 kỳ dữ liệu, mỗi chiến lược được kiểm tra trên 300 kỳ.

### 5.2. Xác suất lý thuyết

Đây là tỉ lệ trúng kỳ vọng nếu **chọn bừa** k số, coi mỗi giải là ngẫu nhiên đều:

| Loại | Công thức | k = 5 |
|---|---|---|
| `de`, `dekep` | k / 100 | 5,0% |
| `loto`, `kep` | 1 − (1 − k/100)^27 | ≈ 75,0% |

Công thức `loto` là xấp xỉ: xác suất để không giải nào trong 27 giải rơi vào k số đã chọn là (1 − k/100)^27.

### 5.3. Kết quả trên dữ liệu 30/10/2025 – 28/10/2026 (k = 5)

| Loại | hot | gan | combo | random | Lý thuyết |
|---|---|---|---|---|---|
| Đề | 3,3% | 2,7% | 6,0% | 4,7% | 5,0% |
| Loto | 74,0% | 76,3% | 77,0% | 77,7% | 75,0% |
| Lô kép | 71,3% | 74,0% | 74,0% | 72,0% | 75,0% |
| ĐB về kép | 6,3% | 6,0% | 5,0% | 7,0% | 5,0% |

**Cách hiểu:** với 300 kỳ kiểm tra, sai số ngẫu nhiên của một tỉ lệ khoảng
±2,5% (với tỉ lệ 5%) và ±5% (với tỉ lệ 75%). Mọi chênh lệch ở trên đều nằm
trong khoảng này, nên **không chiến lược nào tốt hơn chọn bừa** một cách có ý nghĩa.
Ví dụ, `combo` đạt 6,0% ở đề, tức 18 lần trúng trên 300 kỳ, so với 15 lần kỳ vọng.
Chênh 3 lần như vậy là bình thường do may rủi.

### 5.4. Kiểm định chi-square

Terminal in `chi-square p=…` cho mỗi loại. Phép kiểm định này hỏi: *các con số có ra đều nhau không?*

- **p lớn (> 0,05)**: không có bằng chứng số nào ra nhiều/ít bất thường. Dữ liệu trông giống ngẫu nhiên đều.
- **p nhỏ (< 0,05)**: có dấu hiệu lệch. Nhưng khi kiểm tra nhiều thứ cùng lúc, thỉnh thoảng sẽ có p nhỏ do may rủi.

Kết quả hiện tại: loto p = 0,77, đề p = 0,08, lô kép p = 0,79, ĐB về kép p = 0,94. Không có dấu hiệu lệch.

## 6. Các chỉ số thống kê khác

| Chỉ số | Ý nghĩa | Hiển thị ở |
|---|---|---|
| **Đầu / đuôi ĐB** | Đầu = chữ số hàng chục, đuôi = chữ số hàng đơn vị của 2 số cuối ĐB. Đếm mỗi chữ số 0–9 xuất hiện bao nhiêu lần | Báo cáo HTML |
| **Chẵn / lẻ** | Tỉ lệ kỳ có 2 số cuối ĐB là số chẵn / lẻ | Báo cáo HTML |
| **To / nhỏ** | To = 50–99, nhỏ = 00–49 | Báo cáo HTML |
| **Lô về nhiều nháy** | Trong 30 kỳ gần nhất, mỗi lô có bao nhiêu kỳ về từ 2 lần trở lên trong cùng 1 kỳ | Báo cáo HTML |
| **10 lần ĐB về kép gần nhất** | Ngày và số kép | Báo cáo HTML |
| **Bảng "đề hôm sau"** | Đuôi (hoặc đầu) ĐB hôm nay → phân bố đuôi ĐB kỳ kế tiếp | Chỉ trong Python: `analysis.follow_db(df)` |

## 7. Đọc kết quả trên terminal và báo cáo HTML

### Terminal

```
=== 2 số cuối giải Đặc biệt — chi-square p=0.079 ===
so  diem  ra_30_ky  ra_tong  gan  gan_max
54 0.753         2       10   22       82
...
Backtest (tỉ lệ kỳ trúng ≥1 trong 5 số):
hot          0.033
gan          0.027
combo        0.060
random       0.043
ly_thuyet    0.050
```

| Cột | Ý nghĩa |
|---|---|
| `so` | Con số gợi ý |
| `diem` | Điểm của chiến lược `combo` (0–1) |
| `ra_30_ky` | Số lần ra trong 30 kỳ gần nhất |
| `ra_tong` | Số lần ra trong toàn bộ dữ liệu |
| `gan` | Số kỳ hiện đang chưa ra |
| `gan_max` | Gan dài nhất từng có |

### Báo cáo HTML (`reports/report.html`)

1. **Thanh công cụ và Kết quả mới nhất**: 2 nút (xem [mục 2](#2-sử-dụng-hằng-ngày)) và bảng kết quả đầy đủ 27 số của kỳ gần nhất theo từng giải.
1. **Gợi ý kỳ tới**: mỗi loại một thẻ gồm k số gợi ý, bảng điểm chi tiết (bấm "Chi tiết điểm") và bảng backtest.
2. **Thống kê kép & đặc biệt**: tỉ lệ ĐB về kép, gan kép, lô kép trung bình, chẵn/lẻ, to/nhỏ, 10 lần ĐB về kép gần nhất, lô về nhiều nháy.
3. **Biểu đồ**: tần suất ĐB và loto 00–99 (cột **màu cam** là số được gợi ý), top 20 lô gan, top 20 đề gan, đầu/đuôi ĐB. Rê chuột lên cột để xem số liệu.
4. **30 kỳ gần nhất**: ngày, 2 số cuối ĐB và 27 lô đã sắp xếp.

Báo cáo không cần Internet và tự đổi sang giao diện tối theo cài đặt máy.

## 8. Dữ liệu

- **Nguồn:** rongbachkim.com, thông qua địa chỉ JSON mà trang `ketqua.html` dùng:
  `https://rongbachkim.com/ketqua.php?getkq&ngay=YYYY-MM-DD&days=N&wday=0` (tối đa 300 ngày mỗi lần gọi).
- **File:** `data/raw/results.csv`
  ```
  date,numbers
  2026-10-28,74175 18190 62731 30468 ... 249 58 30 05 41
  ```
  Cột `numbers` gồm 27 số **đầy đủ** theo thứ tự giải: ĐB, G1, G2 (2), G3 (6), G4 (4), G5 (6), G6 (3), G7 (4).
  Số đầu tiên luôn là giải Đặc biệt.
- Các ngày nghỉ Tết không quay thưởng nên 1 năm có khoảng 360 kỳ.
- Có thể tự nhập dữ liệu từ nguồn khác, miễn đúng định dạng trên.

## 9. Lỗi thường gặp

| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| `ModuleNotFoundError: No module named 'pandas'` | Chưa kích hoạt môi trường: chạy `source .venv/bin/activate` |
| `Không thấy .../results.csv, dùng dữ liệu ngẫu nhiên mẫu` | Chưa tải dữ liệu: chạy `python -m src.crawler` |
| `Thêm 0 ngày mới` | Đã có dữ liệu mới nhất, hoặc kỳ hôm nay chưa quay hay trang nguồn chưa cập nhật |
| `Cảnh báo: <ngày> có N số (kỳ vọng 27)` | Trang nguồn trả về thiếu số (thường do lấy lúc đang quay). Xóa dòng ngày đó trong CSV rồi chạy lại crawler sau |
| `Address already in use` khi chạy server | Cổng 8000 đang bị dùng (có thể server cũ chưa tắt). Dùng `--port 8001` |
| Bấm nút báo "Đang xử lý yêu cầu trước" | Đợi lần bấm trước chạy xong rồi bấm lại |
| Lỗi mạng / `HTTPError` / timeout | Trang nguồn chậm hoặc đổi cấu trúc. Thử lại sau; nếu vẫn lỗi, cần sửa `API_URL` trong `src/crawler.py` |

## 10. Sử dụng từ Python

```python
from src.data_loader import load_results
from src import analysis, predict

df = load_results()                                   # cột: date, numbers, db

predict.predict(df, target="de", k=5)                 # gợi ý theo combo
predict.predict(df, target="loto", k=5, strategy="hot")
predict.backtest(df, target="kep", k=5)

analysis.gan(df, "loto").head(10)                     # top 10 lô gan
analysis.max_gan(df, "de")                            # gan cực đại của đề
analysis.frequency(df, "de", window=60)               # tần suất ĐB 60 kỳ gần nhất
analysis.dau_duoi(df, "de")                           # đầu / đuôi ĐB
analysis.follow_db(df, by="duoi")                     # bảng "đề hôm sau"
analysis.kep_stats(df)
```

**Thêm chiến lược mới:** viết hàm nhận ma trận `m` (numpy, số kỳ × số con số) và trả về
mảng điểm, rồi đăng ký vào `STRATEGIES` trong `src/predict.py`. Backtest và báo cáo
sẽ tự động có thêm chiến lược đó. Ví dụ:

```python
def score_hot60(m):
    """Ra nhiều trong 60 kỳ gần nhất."""
    return m[-60:].sum(0).astype(float)

STRATEGIES = {..., "hot60": score_hot60}
```

Sau đó cần thêm tên hiển thị cho `"hot60"` vào `STRATEGY_NAMES` trong `src/report.py`.

## 11. Chạy tự động trên GitHub (không cần máy cá nhân)

### 11.1. Cách hoạt động

File `.github/workflows/daily.yml` ra lệnh cho GitHub, mỗi ngày lúc **18h40** và **20h30** (giờ VN):

1. Bật một máy chủ Linux, cài Python và thư viện.
2. Chạy `python -m src.crawler` để tải kết quả mới, rồi lưu (commit) `data/raw/results.csv` vào repo.
3. Chạy `python -m src.predict --site site` để tính dự đoán kỳ tiếp theo và tạo trang tĩnh.
4. Đăng trang lên **GitHub Pages**: `https://<tên-tài-khoản>.github.io/xoso-prediction/`.

Lần chạy 20h30 là chạy bù, phòng khi lần 18h40 bị GitHub làm trễ hoặc trang nguồn chưa có đủ kết quả.
Mỗi lần chạy mất khoảng 1–2 phút. Repo công khai được chạy **miễn phí, không giới hạn**.

Trang trên GitHub Pages **không có 2 nút** (vì không có server Python). Thay vào đó, đầu trang có
link **"Run workflow trên GitHub"** để cập nhật ngay khi cần.

### 11.2. Cài đặt (làm 1 lần)

**Bước 1 — Tạo tài khoản và repo**

1. Đăng ký tài khoản tại https://github.com (miễn phí).
2. Bấm **+** (góc trên phải) → **New repository**.
3. *Repository name*: `xoso-prediction` · chọn **Public** · **không** tick "Add a README" → **Create repository**.

**Bước 2 — Đưa code lên GitHub**

Cách dễ nhất là dùng ứng dụng **GitHub Desktop** (https://desktop.github.com):

1. Cài và đăng nhập GitHub Desktop.
2. **File → Add Local Repository…** → chọn thư mục `~/xoso-prediction`.
   Nếu ứng dụng báo thư mục chưa phải git repo, bấm **create a repository** (giữ nguyên các tùy chọn).
3. Ô *Summary* ở góc dưới trái nhập `Khởi tạo` → **Commit to main**.
4. Bấm **Publish repository**, **bỏ tick** "Keep this code private" → **Publish**.

> Dùng dòng lệnh thay cho GitHub Desktop:
> ```bash
> cd ~/xoso-prediction
> git init -b main && git add . && git commit -m "Khởi tạo"
> git remote add origin https://github.com/<tên-tài-khoản>/xoso-prediction.git
> git push -u origin main
> ```
> Khi hỏi mật khẩu, dán **Personal access token** (GitHub → Settings → Developer settings →
> Personal access tokens), không phải mật khẩu đăng nhập.

**Bước 3 — Bật GitHub Pages**

Trên trang repo: **Settings → Pages** → mục *Build and deployment* → *Source*: chọn **GitHub Actions**.

**Bước 4 — Chạy lần đầu**

1. Tab **Actions** → chọn **Cập nhật XSMB hằng ngày** ở cột trái → **Run workflow** → **Run workflow**.
2. Đợi 1–2 phút đến khi có dấu ✓ màu xanh.
3. Mở `https://<tên-tài-khoản>.github.io/xoso-prediction/`. Có thể lưu link này vào màn hình chính điện thoại.

Từ đây trở đi, máy tính của bạn có thể tắt; trang tự cập nhật mỗi tối.

### 11.3. Sử dụng hằng ngày

| Việc | Cách làm |
|---|---|
| Xem dự đoán | Mở link GitHub Pages |
| Cập nhật ngay (không đợi lịch) | Link "Run workflow trên GitHub" ở đầu trang, hoặc tab **Actions** → **Run workflow**. Có ô nhập số gợi ý (1–20). Dùng được cả trên app GitHub cho điện thoại |
| Xem lịch sử dữ liệu | Repo → file `data/raw/results.csv` → **History** (mỗi ngày một lần commit) |
| Biết khi có lỗi | GitHub tự gửi email khi một lần chạy thất bại |

### 11.4. Sửa code sau khi đã đưa lên GitHub

Mỗi tối GitHub tự commit dữ liệu mới, nên bản trên máy bạn sẽ cũ dần. **Trước khi sửa code, luôn lấy bản mới về**
(GitHub Desktop: **Fetch origin → Pull**; dòng lệnh: `git pull`), sửa xong thì commit và push như Bước 2.

### 11.5. Lỗi thường gặp khi chạy trên GitHub

| Hiện tượng | Cách xử lý |
|---|---|
| Bước "Tải kết quả mới nhất" lỗi `HTTPError 403` / timeout | rongbachkim.com chặn hoặc chậm với máy chủ GitHub. Thử chạy lại; nếu lỗi kéo dài, cần đổi nguồn dữ liệu |
| Bước "Lưu dữ liệu vào repo" lỗi `Permission denied` / `403` | **Settings → Actions → General → Workflow permissions** → chọn **Read and write permissions** → Save |
| Bước deploy lỗi `Pages not enabled` / `Get Pages site failed` | Chưa làm Bước 3 (Source phải là **GitHub Actions**) |
| Lịch chạy trễ 10–30 phút | Bình thường với GitHub vào giờ cao điểm; lần chạy 20h30 sẽ bù |
| Push code bị từ chối (`rejected … fetch first`) | Máy bạn đang có bản cũ: Pull trước rồi push lại |
