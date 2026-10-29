"""Web server chạy trên máy: phục vụ báo cáo và 2 nút trên trang.

    python -m src.server [--port 8000]

- GET  /              báo cáo HTML (tự tạo nếu chưa có)
- POST /api/update    tải kết quả mới nhất từ rongbachkim.com rồi tính lại báo cáo
- POST /api/predict   tính lại dự đoán kỳ tiếp theo (tham số ?k=5)
"""
import argparse
import json
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pandas as pd

from . import crawler
from .predict import build_report
from .report import REPORT_FILE

_lock = threading.Lock()  # tránh chạy crawler/backtest song song khi bấm nút liên tục
_state = {"k": 5}


def _parse_k(query: str) -> int:
    k = int(parse_qs(query).get("k", [_state["k"]])[0])
    if not 1 <= k <= 20:
        raise ValueError("Số gợi ý phải từ 1 đến 20")
    return k


class UserError(Exception):
    """Lỗi có thông báo tiếng Việt hiển thị thẳng cho người dùng."""


def do_update(k: int) -> dict:
    try:
        added, pending = crawler.update()
    except (OSError, TimeoutError) as e:  # URLError, HTTPError, mất mạng, timeout
        raise UserError("Không tải được dữ liệu từ rongbachkim.com — kiểm tra kết nối mạng "
                        f"hoặc thử lại sau ít phút. (chi tiết: {e})") from e
    except ValueError as e:  # JSON không hợp lệ
        raise UserError("rongbachkim.com trả về dữ liệu không đọc được, có thể trang đang "
                        f"bảo trì hoặc đã đổi cấu trúc. Thử lại sau. (chi tiết: {e})") from e
    df, _, _ = build_report(k)
    last = df["date"].max()
    msg = (f"Đã thêm {added} kỳ mới, kết quả mới nhất ngày {last:%d/%m/%Y}." if added
           else f"Chưa có kết quả mới (mới nhất: {last:%d/%m/%Y}).")
    if pending:
        msg += f" Kỳ {', '.join(pending)} đang quay, chưa đủ số — bấm lại sau khoảng 18h35."
    return {"added": added, "latest": f"{last:%Y-%m-%d}", "message": msg}


def do_predict(k: int) -> dict:
    df, results, _ = build_report(k)
    nxt = df["date"].max() + pd.Timedelta(days=1)
    picks = {t: r["predict"]["so"].tolist() for t, r in results.items()}
    return {"date": f"{nxt:%Y-%m-%d}", "k": k, "picks": picks,
            "message": f"Đã dự đoán kỳ {nxt:%d/%m/%Y} ({k} số mỗi loại)."}


ACTIONS = {"/api/update": do_update, "/api/predict": do_predict}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, ctype: str):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: dict):
        self._send(status, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self):
        if urlparse(self.path).path not in ("/", "/index.html", "/report.html"):
            return self._send(404, b"Not found", "text/plain")
        with _lock:
            if not REPORT_FILE.exists():
                build_report(_state["k"])
        self._send(200, REPORT_FILE.read_bytes(), "text/html; charset=utf-8")

    def do_POST(self):
        url = urlparse(self.path)
        action = ACTIONS.get(url.path)
        if not action:
            return self._json(404, {"error": "Không có API này"})
        try:
            k = _parse_k(url.query)
        except ValueError as e:
            return self._json(400, {"error": str(e)})
        if not _lock.acquire(blocking=False):
            return self._json(409, {"error": "Đang xử lý yêu cầu trước, thử lại sau ít giây"})
        try:
            _state["k"] = k
            self._json(200, action(k))
        except UserError as e:
            self._json(502, {"error": str(e)})
        except Exception as e:
            traceback.print_exc()
            self._json(500, {"error": "Lỗi không mong muốn khi xử lý, xem chi tiết trong cửa sổ "
                                      f"terminal đang chạy server. ({type(e).__name__}: {e})"})
        finally:
            _lock.release()


def main():
    parser = argparse.ArgumentParser(description="Server cho trang thống kê XSMB")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true", help="không tự mở trình duyệt")
    args = parser.parse_args()
    # chỉ lắng nghe trên máy này, không mở ra mạng ngoài
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://localhost:{args.port}"
    print(f"Đang chạy tại {url}  (Ctrl+C để dừng)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng server.")


if __name__ == "__main__":
    main()
