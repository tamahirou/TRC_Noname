# aruco7_uart.py  (UnitV2 / OpenCV 3.4.9 用, DICT_7X7_1000)
# USE_UART = False : IDをprintするだけ（動作確認用）
# USE_UART = True  : IDをUARTへ "ID\n" で送信
import cv2, json, os, time
import numpy as np

USE_UART = False
PORT, BAUD = "/dev/ttyS0", 115200   # 要確認（GroveのUART）
TABLE_PATH = "/home/m5stack/dict7x7_1000.json"

W, H = 320, 240
CELL = 8
SZ = CELL * 9
MIN_AREA = 400                      # 小さすぎる四角形は無視（要調整）

TABLE = json.load(open(TABLE_PATH))

# ---- 出力 ----
ser = None
if USE_UART:
    try:
        import serial
        ser = serial.Serial(PORT, BAUD, timeout=0)
        def send(s):
            ser.write(s.encode())
    except ImportError:
        import termios
        fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY)
        attr = termios.tcgetattr(fd)
        attr[0] = 0; attr[1] = 0; attr[3] = 0
        attr[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        speed = getattr(termios, "B%d" % BAUD)
        attr[4] = speed; attr[5] = speed
        termios.tcsetattr(fd, termios.TCSANOW, attr)
        def send(s):
            os.write(fd, s.encode())
else:
    def send(s):
        print(s.strip())

# ---- カメラ ----
cap = cv2.VideoCapture(0)
cap.set(3, W)
cap.set(4, H)

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
    # 外周1マスは全部黒のはず
    if cells[0].any() or cells[-1].any() or cells[:, 0].any() or cells[:, -1].any():
        return None
    inner = cells[1:8, 1:8].astype(np.uint8).flatten()
    code = int("".join(map(str, inner)), 2)
    return TABLE.get(str(code))

if not cap.isOpened():
    print("camera open failed (標準ファンクションがカメラを掴んでいる可能性)")

while True:
    ok, frame = cap.read()
    if not ok:
        continue
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY_INV, 21, 7)
    cnts = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[-2]
    ids = set()
    for c in cnts:
        if cv2.contourArea(c) < MIN_AREA:
            continue
        ap = cv2.approxPolyDP(c, 0.03 * cv2.arcLength(c, True), True)
        if len(ap) != 4 or not cv2.isContourConvex(ap):
            continue
        quad = order_cw(ap.reshape(4, 2).tolist())
        mid = decode(gray, quad)
        if mid is not None:
            ids.add(mid)
    for mid in sorted(ids):
        send("%d\n" % mid)