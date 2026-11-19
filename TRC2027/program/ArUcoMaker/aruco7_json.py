# aruco7_json.py  (UnitV2 / OpenCV 3.4.9, DICT_7X7_1000)
# 管理プログラム(server_core.py)の子プロセスとして動かす版。
# 標準出力に {"aruco":[ID,...]} を1行ずつ出すと、管理プログラムが
# /dev/ttyS1 (115200bps) に「その行 + \r\n」で転送する。UARTは自分で開かない。
import cv2, json, sys, time
import numpy as np

TABLE_PATH = "/home/m5stack/dict7x7_1000.json"
W, H = 320, 240
CELL = 8
SZ = CELL * 9
MIN_AREA = 400

TABLE = json.load(open(TABLE_PATH))

cap = None
for _ in range(10):                 # 前の機能が終了してカメラが空くまで待つ
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        break
    cap.release()
    time.sleep(1)
if cap is None or not cap.isOpened():
    sys.stderr.write("camera open failed\n")
    sys.exit(1)
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
    cells = w.reshape(9, CELL, 9, CELL).mean(axis=(1, 3)) > 127
    if cells[0].any() or cells[-1].any() or cells[:, 0].any() or cells[:, -1].any():
        return None
    inner = cells[1:8, 1:8].astype(np.uint8).flatten()
    code = int("".join(map(str, inner)), 2)
    return TABLE.get(str(code))

while True:
    ok, frame = cap.read()
    if not ok:
        time.sleep(0.01)
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
    if ids:
        # 必ずflush。キーは img/meta/render/web 以外にする（UART転送の条件）
        print(json.dumps({"aruco": sorted(ids)}), flush=True)