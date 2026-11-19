# aruco_server.py  (UnitV2 / Python3 / OpenCV 3.4.9, DICT_7X7_1000)
#  - ArUcoのIDを検出して UART(/dev/ttyS1) に "ID\n" で送信
#  - ブラウザで http://<UnitV2のIP>/ を開くと、ライブ映像 + 検出結果オーバーレイを表示
#  - 標準のpayload(管理プログラム)には一切依存しない独立プログラム
import cv2, json, sys, time, threading
import numpy as np
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# ---------------- 設定 ----------------
TABLE_PATH = "/home/m5stack/dict7x7_1000.json"
UART_PORT, UART_BAUD = "/dev/ttyS1", 115200
HTTP_PORTS = (80, 8080)        # 80が使えなければ8080
W, H = 320, 240                # 解像度。遠くを読みたいなら 640, 480 (fpsは下がる)
MIN_AREA = 400                 # 小さすぎる四角形を無視(px^2)
JPEG_QUALITY = 60
DRAW_CANDIDATES = False        # Trueで「四角形だがIDに読めなかったもの」を赤線で表示(調整用)
# --------------------------------------

CELL = 8
SZ = CELL * 9


def log(msg):
    print(msg, flush=True)


TABLE = json.load(open(TABLE_PATH))

# ---- UART ----
ser = None
try:
    import serial
    ser = serial.Serial(UART_PORT, UART_BAUD, timeout=0, write_timeout=0.1)
    log("uart open: %s %d" % (UART_PORT, UART_BAUD))
except Exception as e:
    log("uart disabled: %r" % (e,))


def uart_send(mid):
    if ser is None:
        return
    try:
        ser.write(("%d\n" % mid).encode())
    except Exception:
        pass


# ---- 共有状態 ----
cond = threading.Condition()
state = {"jpeg": None, "seq": 0, "ids": [], "fps": 0.0, "clients": 0}

# ---- 検出 ----
DST = np.float32([[0, 0], [SZ, 0], [SZ, SZ], [0, SZ]])


def order_cw(pts):
    c = 0
    for i in range(4):
        a, b, d = pts[i], pts[(i + 1) % 4], pts[(i + 2) % 4]
        c += (b[0] - a[0]) * (d[1] - b[1]) - (b[1] - a[1]) * (d[0] - b[0])
    return pts if c > 0 else pts[::-1]


def decode(gray, quad):
    M = cv2.getPerspectiveTransform(np.float32(quad), DST)
    w = cv2.warpPerspective(gray, M, (SZ, SZ))
    _, w = cv2.threshold(w, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    cells = w.reshape(9, CELL, 9, CELL).mean(axis=(1, 3)) > 127   # True=白
    if cells[0].any() or cells[-1].any() or cells[:, 0].any() or cells[:, -1].any():
        return None
    inner = cells[1:8, 1:8].astype(np.uint8).flatten()
    code = int("".join(map(str, inner)), 2)
    return TABLE.get(str(code))


def detect(gray):
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY_INV, 21, 7)
    cnts = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[-2]
    found, rejected = [], []
    for c in cnts:
        if cv2.contourArea(c) < MIN_AREA:
            continue
        ap = cv2.approxPolyDP(c, 0.03 * cv2.arcLength(c, True), True)
        if len(ap) != 4 or not cv2.isContourConvex(ap):
            continue
        quad = order_cw(ap.reshape(4, 2).tolist())
        mid = decode(gray, quad)
        if mid is not None:
            found.append((mid, quad))
        else:
            rejected.append(quad)
    return found, rejected


def draw(frame, found, rejected, fps):
    if DRAW_CANDIDATES:
        for q in rejected:
            cv2.polylines(frame, [np.array(q, np.int32).reshape(-1, 1, 2)],
                          True, (0, 0, 255), 1)
    for mid, q in found:
        pts = np.array(q, np.int32).reshape(-1, 1, 2)
        cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
        cv2.circle(frame, (int(q[0][0]), int(q[0][1])), 4, (0, 255, 255), -1)
        cv2.putText(frame, "ID %d" % mid, (int(q[0][0]), max(12, int(q[0][1]) - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(frame, "%.1f fps" % fps, (4, 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)


# ---- カメラ ----
def open_cam():
    while True:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            cap.set(3, W)
            cap.set(4, H)
            log("camera opened")
            return cap
        cap.release()
        log("camera busy, retry")
        time.sleep(1)


def main_loop():
    cap = open_cam()
    fails = 0
    t0, n, fps = time.time(), 0, 0.0
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            fails += 1
            if fails > 50:
                cap.release()
                cap = open_cam()
                fails = 0
            time.sleep(0.01)
            continue
        fails = 0
        if frame.ndim == 2:
            gray = frame
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        found, rejected = detect(gray)
        ids = sorted(set(m for m, _ in found))
        for mid in ids:
            uart_send(mid)

        n += 1
        now = time.time()
        if now - t0 >= 1.0:
            fps = n / (now - t0)
            t0, n = now, 0

        jpg = None
        if state["clients"] > 0:       # 見ている人がいる時だけ描画・JPEG化
            draw(frame, found, rejected, fps)
            okj, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if okj:
                jpg = buf.tobytes()

        with cond:
            state["ids"] = ids
            state["fps"] = fps
            if jpg is not None:
                state["jpeg"] = jpg
                state["seq"] += 1
            cond.notify_all()


# ---- HTTP ----
PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UnitV2 ArUco</title>
<style>body{font-family:sans-serif;margin:12px;background:#111;color:#eee}
img{width:100%;max-width:640px;display:block;background:#000}
#ids{font-size:1.6em;margin:8px 0}</style></head><body>
<img src="/stream">
<div id="ids">ID: -</div><div id="fps"></div>
<script>
function tick(){fetch('/ids').then(function(r){return r.json();}).then(function(d){
document.getElementById('ids').textContent='ID: '+(d.ids.length?d.ids.join(', '):'-');
document.getElementById('fps').textContent=d.fps.toFixed(1)+' fps';
}).catch(function(){});}
setInterval(tick,300);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/ids":
            with cond:
                body = json.dumps({"ids": state["ids"], "fps": state["fps"]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/stream":
            self.stream()
        else:
            self.send_error(404)

    def stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        with cond:
            state["clients"] += 1
        try:
            last = -1
            while True:
                with cond:
                    while state["seq"] == last or state["jpeg"] is None:
                        cond.wait(1.0)
                    last = state["seq"]
                    jpg = state["jpeg"]
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                 + str(len(jpg)).encode() + b"\r\n\r\n")
                self.wfile.write(jpg)
                self.wfile.write(b"\r\n")
        except Exception:
            pass
        finally:
            with cond:
                state["clients"] -= 1


class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_http():
    for port in HTTP_PORTS:
        try:
            srv = Server(("0.0.0.0", port), Handler)
        except OSError as e:
            log("port %d unavailable: %r" % (port, e))
            continue
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        log("http listening on port %d" % port)
        return
    log("http disabled")


if __name__ == "__main__":
    start_http()
    main_loop()