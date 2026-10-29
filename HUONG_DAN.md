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
python -m pytest   # kết quả mong đợi: 22 passed
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
| **Dự đoán kỳ dd/mm/yyyy** | Tính dự đoán đầy đủ cho kỳ tiếp theo kèm backtest: **Loto 3 số · Đề 10 số · Lô kép 2 số · Cặp lô lộn 1 cặp** |

Mỗi lần bấm mất khoảng 10 giây (do chạy backtest 11 chiến lược trên 5 năm dữ liệu), xong trang tự tải lại.
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

Lần chạy đầu tiên, `crawler` tải toàn bộ 5 năm gần nhất (~1.800 kỳ, mất khoảng 10 giây).
Những lần sau nó chỉ tải các ngày mới hơn ngày gần nhất trong file. Dữ liệu cũ **không bao giờ bị xóa**.

## 3. Các tùy chọn dòng lệnh

### `python -m src.crawler`

| Tùy chọn | Mặc định | Ý nghĩa |
|---|---|---|
| `--days N` | (không) | Đảm bảo dữ liệu phủ ít nhất N ngày lịch tính lùi từ hôm nay |
| `--years N` | (không) | Như `--days` nhưng tính theo năm, ví dụ `--years 10` |

Mỗi lần chạy, crawler:

1. tải các kỳ **mới hơn** kỳ gần nhất trong file (cập nhật hằng ngày);
2. nếu có `--days`/`--years` mà dữ liệu chưa phủ đủ, tải **bù các kỳ cũ hơn** kỳ cũ nhất trong file;
3. nếu file chưa có, tải 5 năm gần nhất;
4. bỏ qua kỳ chưa đủ 27 số (đang quay) để lần sau tải lại; tự thử lại 3 lần khi lỗi mạng.

Không bao giờ xóa dữ liệu đã có. Muốn bớt dữ liệu thì tự xóa dòng trong CSV.

### `python -m src.predict`

| Tùy chọn | Mặc định | Ý nghĩa |
|---|---|---|
| `--target` | `all` | Loại dự đoán: `loto`, `de`, `kep`, `cap` hoặc `all` |
| `--k N` | (không) | Dùng cùng N số gợi ý cho mọi loại. Không truyền thì dùng mặc định: loto 3, đề 10, kép 2, cặp lộn 1 cặp |
| `--report` | tắt | Tạo thêm file `reports/report.html` |
| `--site DIR` | tắt | Tạo trang tĩnh `DIR/index.html` không có nút (dùng cho GitHub Pages) |
| `--no-record` | tắt | Không ghi dự đoán vào sổ theo dõi (xem mục 5.6) — dùng khi chỉ muốn thử |

### `python -m src.tracking`

Xem thống kê dự đoán thực tế đã ghi trong sổ theo dõi (mục 5.6).

| Tùy chọn | Mặc định | Ý nghĩa |
|---|---|---|
| `--k N` | (không) | Xem các dự đoán được ghi với cùng N số cho mọi loại (mặc định: số gợi ý hiện tại) |
| `--strategy S` | `combo` | Chiến lược xem chi tiết từng kỳ |
| `--last N` | 15 | Số kỳ gần nhất hiển thị chi tiết |

Ý nghĩa các loại dự đoán:

| `--target` | Tên gọi | Mỗi kỳ được tính là "ra" những số nào |
|---|---|---|
| `de` | Đề / 2 số cuối giải Đặc biệt | 1 số: 2 chữ số cuối của giải ĐB |
| `loto` | Lô tô | 27 số: 2 chữ số cuối của cả 27 giải (ĐB, G1, 2×G2, 6×G3, 4×G4, 6×G5, 3×G6, 4×G7) |
| `kep` | Lô kép | Các số kép (00, 11, 22, …, 99) nằm trong 27 lô ở trên |
| `cap` | Cặp lô lộn | 45 cặp số lộn (01-10, …, 59-95, …, 89-98) trong 27 lô. Cặp "về" nếu **ít nhất 1 trong 2 số** về. Số kép không có cặp lộn nên không thuộc loại này |

Số gợi ý mặc định: **Loto 3 · Đề 10 · Lô kép 2 · Cặp lộn 1 cặp**. Loto và đề xếp hạng cả 100 số,
nên có thể gồm cả số kép. Muốn đổi mặc định thì sửa `SUGGEST_K` trong `src/predict.py`.

Ví dụ:

```bash
python -m src.predict                         # cả 4 loại với số gợi ý mặc định
python -m src.predict --target cap            # chỉ xem cặp lô lộn
python -m src.predict --target de --k 20 --no-record   # thử 20 số cho đề, không ghi sổ
```

## 4. Thuật toán dự đoán

### 4.1. Dữ liệu đầu vào: ma trận lịch sử

Với mỗi loại dự đoán, dữ liệu được chuyển thành một **ma trận M**:

- mỗi **dòng** là một kỳ quay, xếp từ cũ đến mới;
- mỗi **cột** là một con số có thể ra (00–99 với `de`/`loto`, 10 số kép với `kep`, 45 cặp lộn với `cap`);
- `M[kỳ, số]` = số lần con số đó xuất hiện trong kỳ đó (với `loto` có thể là 2, 3 nếu về nhiều nháy;
  với `cap` là tổng số lần về của cả 2 số trong cặp).

Từ ma trận này tính ra 3 đại lượng cơ bản cho mỗi con số:

| Đại lượng | Cách tính | Ví dụ |
|---|---|---|
| **Tần suất 30 kỳ** | Tổng số lần xuất hiện trong 30 kỳ gần nhất | Lô 75 về 21 lần trong 30 kỳ |
| **Tần suất tổng** | Tổng số lần xuất hiện trong toàn bộ dữ liệu | Lô 14 về 484 lần trong 1.805 kỳ |
| **Gan** | Số kỳ liên tiếp **gần nhất** con số chưa xuất hiện. Gan = 0 nghĩa là kỳ vừa rồi có về | Lô 51 gan 15 kỳ |
| **Gan max** | Chuỗi kỳ **dài nhất** trong lịch sử mà con số không xuất hiện | Lô 51 từng gan tối đa 22 kỳ |

> Nếu một số **chưa từng ra** trong toàn bộ dữ liệu, gan = số kỳ của dữ liệu (ví dụ 360).

### 4.2. Bốn chiến lược chấm điểm cơ bản

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

Ví dụ với lô 51 (kỳ 29/10/2026): ra 12 lần/30 kỳ, 463 lần tổng (5 năm), gan 15 / gan max 22.
Thành phần gan = 15/22 ≈ 0.68.

Trọng số 0.4 / 0.3 / 0.3 là **chọn tay**, không được tối ưu từ dữ liệu.
Muốn thử trọng số khác thì sửa hàm `score_combo` trong `src/predict.py`.

#### d) `random` — ngẫu nhiên

```
điểm = số ngẫu nhiên trong [0, 1)
```

Dùng làm **mốc so sánh**: một chiến lược chỉ có giá trị nếu nó trúng nhiều hơn
chiến lược này một cách ổn định. Mỗi lần chạy, kết quả của `random` sẽ hơi khác nhau.

### 4.3. Các chiến lược bổ sung và cách kết hợp

| Tên | Ý tưởng | Công thức |
|---|---|---|
| `ewma` | Tần suất, kỳ gần đây nặng ký hơn | Σ M[kỳ] × 0,5^(khoảng cách / 20) — kỳ cách 20 kỳ chỉ tính một nửa |
| `bayes` | Tần suất tổng nhưng không tin quá vào dữ liệu ít | (số lần ra + 5) / (tổng + 5 × số con số) — "co" về phân bố đều (Dirichlet) |
| `markov` | Số hôm nay ảnh hưởng số ngày mai | Bảng chuyển tiếp "số A ra hôm nay → số B ra hôm sau", làm trơn +1 |
| `digit` | Tách đầu và đuôi để có nhiều dữ liệu hơn cho mỗi ước lượng | P(đầu) × P(đuôi) trong 60 kỳ (với số kép thì dùng `bayes`) |
| `hazard` | Phiên bản "đo đạc" của nuôi gan | Tỉ lệ thực tế một số ra khi nó đã gan đúng g kỳ, gộp dữ liệu mọi số |

Hai cách **kết hợp** 8 chiến lược cơ sở (`hot`, `gan`, `combo`, `ewma`, `bayes`, `markov`, `digit`, `hazard`):

- **`ensemble` — bỏ phiếu Borda**: đổi điểm của mỗi chiến lược thành **hạng** (0 → 1)
  rồi lấy trung bình. Dùng hạng thay vì điểm vì mỗi chiến lược có thang đo khác nhau.
- **`hedge` — trọng số thích ứng (thuật toán Hedge / multiplicative weights)**: đi lại
  lịch sử từng kỳ; mỗi chiến lược được thưởng = (số lượt trúng trong top 10 của nó) − (mức
  kỳ vọng khi chọn bừa). Trọng số ∝ e^(tổng thưởng / √số kỳ đã học). Chia cho √số kỳ để
  dữ liệu dài không làm trọng số dồn hết vào một chiến lược chỉ vì may mắn. Chiến lược nào đang "hiệu quả"
  sẽ chi phối kết quả; nếu không có chiến lược nào thật sự hiệu quả, trọng số chỉ dao động theo may rủi.

Phần **gợi ý** vẫn dùng `combo`; muốn dùng chiến lược khác thì gọi
`predict.predict(df, strategy="hedge")`.

### 4.4. Thống kê "Đặc biệt về kép"

ĐB về kép không còn phần gợi ý riêng (10 số gợi ý cho đề có thể đã gồm số kép), nhưng hệ thống vẫn in:

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

Với mỗi chiến lược, backtest còn tính:

- **p** — kiểm định nhị thức một phía: nếu chiến lược chỉ ngang chọn bừa, xác suất đạt
  tỉ lệ trúng cao như vậy (hoặc hơn) do may rủi là bao nhiêu.
- **p_holm** — p đã **hiệu chỉnh Holm** vì đang thử 11 chiến lược cùng lúc. Thử càng nhiều
  chiến lược thì càng dễ có một cái "trông như thắng" do may rủi. Chỉ khi **p_holm < 0,05**
  mới nên coi là dấu hiệu đáng chú ý.

60 kỳ đầu (`warmup`) chỉ dùng làm lịch sử ban đầu. Với 1.805 kỳ dữ liệu, mỗi chiến lược được kiểm tra trên 1.745 kỳ.

### 5.2. Xác suất lý thuyết

Đây là tỉ lệ trúng kỳ vọng nếu **chọn bừa** k số, coi mỗi giải là ngẫu nhiên đều:

| Loại | Công thức | Với số gợi ý mặc định |
|---|---|---|
| `de` | k / 100 | 10 số → 10,0% |
| `loto`, `kep` | 1 − (1 − k/100)^27 | loto 3 số → 56,1%; kép 2 số → 42,0% |
| `cap` | 1 − (1 − 2k/100)^27 (mỗi cặp gồm 2 số) | 1 cặp → 42,0% |

Công thức `loto` là xấp xỉ: xác suất để không giải nào trong 27 giải rơi vào k số đã chọn là (1 − k/100)^27.

### 5.3. Kết quả trên 5 năm dữ liệu 30/10/2021 – 28/10/2026

**Với số gợi ý mặc định hiện tại** (1.745 kỳ kiểm tra; không ô nào có p < 0,05):

| Chiến lược | Đề (10 số) | Loto (3 số) | Lô kép (2 số) | Cặp lộn (1 cặp) |
|---|---|---|---|---|
| hot | 8,9% | 57,2% | 41,8% | 43,7% |
| gan | 9,2% | 56,4% | 42,6% | 42,1% |
| combo | 9,3% | 57,0% | 41,4% | 42,7% |
| ewma | 10,0% | 56,2% | 41,6% | 43,8% |
| bayes | 9,1% | 56,3% | 42,8% | 41,0% |
| markov | 9,4% | 55,0% | 41,3% | 40,2% |
| digit | 8,4% | 56,8% | 42,8% | 41,0% |
| hazard | 9,9% | 55,6% | 40,6% | 42,1% |
| ensemble | 9,4% | 55,4% | 41,7% | 41,1% |
| hedge | 9,8% | 57,2% | 41,6% | 42,2% |
| **Lý thuyết** | **10,0%** | **56,1%** | **42,0%** | **42,0%** |

**Nghiên cứu ban đầu với k = 5 cho mọi loại** (khi còn loại ĐB về kép):

1.745 kỳ kiểm tra. Ô có p < 0,05 (trước hiệu chỉnh) được ghi kèm p.

| Chiến lược | Đề | Loto | Lô kép | ĐB về kép |
|---|---|---|---|---|
| hot | 4,8% | 75,3% | 73,2% | 4,3% |
| gan | 4,8% | 75,0% | 75,6% | 5,9% (p = 0,05; p_holm = 0,55) |
| combo | 4,9% | 75,1% | 74,6% | 4,6% |
| ewma | 4,8% | 75,1% | 73,0% | 3,7% |
| bayes | 4,6% | 74,7% | 74,6% | 4,2% |
| markov | 4,9% | 75,2% | 73,6% | 4,4% |
| digit | 4,5% | 75,5% | 74,6% | 4,2% |
| hazard | 5,0% | 75,0% | 73,7% | 5,4% |
| ensemble | 4,9% | 74,8% | 73,5% | 4,3% |
| hedge | 4,9% | 74,7% | 73,6% | 4,2% |
| **Lý thuyết** | **5,0%** | **75,0%** | **75,0%** | **5,0%** |

(`random` thay đổi mỗi lần chạy nên không ghi vào bảng.)

**Cách hiểu:** với 1.745 kỳ kiểm tra, sai số ngẫu nhiên của một tỉ lệ khoảng ±1%
(với tỉ lệ 5%) và ±2% (với tỉ lệ 75%). Mọi chiến lược đều nằm trong khoảng này
quanh mức lý thuyết. Không ô nào còn ý nghĩa sau hiệu chỉnh Holm.

**So với khi chỉ có 1 năm dữ liệu (360 kỳ):** khi đó `bayes` ở đề đạt 7,7% (p = 0,03)
và `digit` ở loto đạt 79,3% (p = 0,04), trông như "thắng". Với 5 năm, hai con số này về
4,6% và 75,5%, tức là đúng mức chọn bừa. Đây là ví dụ điển hình của **ảo giác do dữ liệu ít**.

**Thí nghiệm đối chứng:** chạy cùng 11 chiến lược × 4 loại trên **20 bộ dữ liệu sinh
hoàn toàn ngẫu nhiên** (360 kỳ, không thể có quy luật), thì **16/20 lần** vẫn có ít nhất
một chiến lược đạt p < 0,05. Một chiến lược "trông như thắng" là chuyện bình thường khi
thử nhiều chiến lược, không phải tín hiệu thật.

### 5.4. Kiểm định trực tiếp các giả thuyết (5 năm)

Thay vì chỉ nhìn tỉ lệ trúng, có thể kiểm tra thẳng ý tưởng đứng sau mỗi chiến lược.
Một lô cụ thể về trong một kỳ với xác suất lý thuyết 1 − 0,99²⁷ = 23,77%. Thực tế trên
5 năm là 23,78%.

| Giả thuyết (chiến lược) | Kết quả trên 1.805 kỳ |
|---|---|
| "Cầu chạy": lô vừa về hôm qua dễ về tiếp (`hot`, `markov`) | Về hôm qua → 23,89% hôm nay; không về hôm qua → 23,75%. Kiểm định độc lập p = 0,57 |
| "Gan lâu phải ra" (`gan`, `hazard`) | Tỉ lệ về khi đang gan 0 / 1–2 / 3–5 / 6–9 / 10–14 / ≥15 kỳ: 23,9 / 23,8 / 23,5 / 23,9 / 23,8 / 24,3%. Không tăng theo gan, mọi p > 0,19 |
| "Đề hôm sau" theo đầu/đuôi ĐB hôm trước | Kiểm định độc lập: đuôi p = 0,90, đầu p = 0,66 |
| Từng chữ số của giải ĐB (5 vị trí) có đều không | p = 0,86 / 0,09 / 0,24 / 0,20 / 0,87 |

Mỗi kỳ quay **độc lập** với kỳ trước, và xác suất **không phụ thuộc** vào việc một số đã gan bao lâu.
Mọi chiến lược trong hệ thống đều dựa trên một trong hai giả định này, nên không thể hơn chọn bừa.

### 5.5. Kiểm định chi-square

Terminal in `chi-square p=…` cho mỗi loại. Phép kiểm định này hỏi: *các con số có ra đều nhau không?*

- **p lớn (> 0,05)**: không có bằng chứng số nào ra nhiều/ít bất thường. Dữ liệu trông giống ngẫu nhiên đều.
- **p nhỏ (< 0,05)**: có dấu hiệu lệch. Nhưng khi kiểm tra nhiều thứ cùng lúc, thỉnh thoảng sẽ có p nhỏ do may rủi.

Kết quả trên 5 năm: loto p = 0,78, đề p = 0,83, lô kép p = 0,64, ĐB về kép p = 0,93. Không có dấu hiệu lệch.
Tách theo từng năm (12 phép thử), loto năm 2022 (p = 0,02) và 2024 (p = 0,02) có p nhỏ, nhưng hai
năm đó không lệch theo cùng một kiểu và các năm khác đều bình thường. Với 12 phép thử, việc có 1–2 p < 0,05 là bình thường.

### 5.6. Theo dõi dự đoán thực tế (sổ dự đoán)

Backtest là **giả lập** trên quá khứ. Để biết hệ thống làm thật ra sao, mỗi lần dự đoán
(lệnh `python -m src.predict`, nút trên trang, hoặc GitHub Actions mỗi tối), hệ thống ghi số
gợi ý kỳ tới của **cả 11 chiến lược × 4 loại** vào `data/predictions.csv`:

```
date,target,strategy,k,numbers,created_at
2026-10-29,cap,combo,1,19,2026-10-29 15:04
2026-10-29,de,combo,10,51 54 42 63 76 77 39 36 62 09,2026-10-29 15:04
```

Quy tắc để sổ luôn trung thực:

- Mỗi (kỳ, loại, chiến lược, k) chỉ ghi **một lần**; chạy lại không ghi đè. Bản ghi đầu tiên được giữ.
- **Không ghi từ 18h ngày quay** (XSMB quay 18h15), nên không thể có dự đoán "ghi sau khi biết kết quả".
- Kỳ nào có kết quả thì được chấm: trúng = ít nhất 1 số gợi ý về. Kỳ không quay (Tết) được bỏ qua.

Kết quả xem ở mục **"Theo dõi dự đoán thực tế"** trên báo cáo HTML (bảng tỉ lệ trúng của phần
gợi ý, bảng mọi chiến lược, và 15 kỳ gần nhất với số đã về được tô màu) hoặc bằng
`python -m src.tracking`.

**Cách đọc:** so cột *Tỉ lệ* với *Lý thuyết*, và xem *p*. Sau vài chục kỳ các con số còn
dao động rất mạnh do may rủi (ví dụ 3 kỳ trúng cả 3 = 100%). Cần **vài trăm kỳ** mới đủ để
kết luận, và như mục 5.3–5.4 cho thấy, nhiều khả năng tỉ lệ sẽ về sát mức lý thuyết.

Cặp lộn được ghi bằng số nhỏ hơn của cặp (`19` = cặp 19-91). Dự đoán ghi với số gợi ý khác
nhau (ví dụ chạy thử `--k 20`) được thống kê riêng; báo cáo chỉ hiển thị dự đoán ghi với số gợi ý mặc định.

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
=== Cặp lô lộn (59-95, ... trong 27 giải) — chi-square p=0.757 ===
   so  diem  ra_30_ky  ra_tong  gan  gan_max
19-91  0.63        24     1038    1       10
Backtest (tỉ lệ kỳ trúng ≥1 trong 1 cặp; p_holm < 0.05 mới đáng chú ý):
           ti_le      p  p_holm
hot        0.437  0.081   0.810
...
combo      0.427  0.299   1.000
...
ly_thuyet  0.420
```

| Cột | Ý nghĩa |
|---|---|
| `so` | Con số gợi ý |
| `diem` | Điểm của chiến lược `combo` (0–1) |
| `ra_30_ky` | Số lần ra trong 30 kỳ gần nhất |
| `ra_tong` | Số lần ra trong toàn bộ dữ liệu |
| `gan` | Số kỳ hiện đang chưa ra |
| `gan_max` | Gan dài nhất từng có |
| `ti_le` | Tỉ lệ kỳ trúng ≥ 1 số trong backtest |
| `p`, `p_holm` | p-value so với chọn bừa, trước và sau hiệu chỉnh Holm (xem mục 5.1) |

### Báo cáo HTML (`reports/report.html`)

- **Đầu trang**: tiêu đề, 2 nút (xem [mục 2](#2-sử-dụng-hằng-ngày)) và giải Đặc biệt kỳ gần nhất.
- **Thanh điều hướng** luôn dính trên đầu khi cuộn: bấm để nhảy nhanh tới từng mục; mục đang xem
  được tô sáng. Nút **◐** đổi giao diện sáng/tối (trình duyệt nhớ lựa chọn). Nút **↑** ở góc phải
  dưới đưa về đầu trang.

Các mục theo thứ tự:

1. **Gợi ý**: 4 thẻ (Loto, Đề, Lô kép, Cặp lộn), số gợi ý hiển thị dạng bóng màu. Mỗi thẻ có
   dòng tóm tắt *tỉ lệ trúng backtest 5 năm* của phần gợi ý so với *chọn bừa*. Bấm "Chi tiết điểm"
   hoặc "Backtest 11 chiến lược" để mở bảng đầy đủ.
2. **Kết quả**: bảng 27 số của kỳ gần nhất theo từng giải.
3. **Theo dõi**: sổ dự đoán thực tế (mục 5.6).
4. **Kép & ĐB**: tỉ lệ ĐB về kép, gan kép, lô kép trung bình, chẵn/lẻ, to/nhỏ, 10 lần ĐB về kép gần nhất, lô về nhiều nháy.
5. **Biểu đồ**: tần suất ĐB và loto 00–99 (cột **màu đỏ** là số được gợi ý), top 20 lô gan, top 20 đề gan, đầu/đuôi ĐB. Rê chuột lên cột để xem số liệu.
6. **30 kỳ**: ngày, 2 số cuối ĐB và 27 lô đã sắp xếp.

Báo cáo không cần Internet. Mặc định theo cài đặt sáng/tối của máy (giao diện tối khi máy không đặt gì).

## 8. Dữ liệu

- **Nguồn:** rongbachkim.com, thông qua địa chỉ JSON mà trang `ketqua.html` dùng:
  `https://rongbachkim.com/ketqua.php?getkq&ngay=YYYY-MM-DD&days=N&wday=0` (tối đa 300 kỳ mỗi lần gọi, có dữ liệu từ năm 2020 trở về trước).
- **File:** `data/raw/results.csv`
  ```
  date,numbers
  2026-10-28,74175 18190 62731 30468 ... 249 58 30 05 41
  ```
  Cột `numbers` gồm 27 số **đầy đủ** theo thứ tự giải: ĐB, G1, G2 (2), G3 (6), G4 (4), G5 (6), G6 (3), G7 (4).
  Số đầu tiên luôn là giải Đặc biệt.
- Các ngày nghỉ Tết (4 ngày) không quay thưởng nên 1 năm có khoảng 361 kỳ. File hiện có 1.805 kỳ (30/10/2021 – 28/10/2026), chỉ thiếu đúng các ngày Tết.
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
