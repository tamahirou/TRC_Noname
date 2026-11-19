# test_decode.py（PCで実行。OpenCVはcontrib入りのままでOK）
import cv2, json, numpy as np

TABLE = json.load(open("dict7x7_1000.json"))
d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_7X7_1000)

CELL = 8
SZ = CELL * 9
DST = np.float32([[0, 0], [SZ, 0], [SZ, SZ], [0, SZ]])

def decode(gray, quad):
    M = cv2.getPerspectiveTransform(np.float32(quad), DST)
    w = cv2.warpPerspective(gray, M, (SZ, SZ))
    _, w = cv2.threshold(w, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    cells = w.reshape(9, CELL, 9, CELL).mean(axis=(1, 3)) > 127
    if cells[0].any() or cells[-1].any() or cells[:, 0].any() or cells[:, -1].any():
        return None
    inner = cells[1:8, 1:8].astype(np.uint8).flatten()
    return TABLE.get(str(int("".join(map(str, inner)), 2)))

ng = 0
for mid in (0, 1, 123, 500, 999):
    for rot in range(4):
        m = cv2.aruco.generateImageMarker(d, mid, 180, None, 1)
        m = np.rot90(m, rot).copy()
        canvas = np.full((260, 260), 255, np.uint8)
        canvas[40:220, 40:220] = m
        quad = [[40, 40], [219, 40], [219, 219], [40, 219]]
        got = decode(canvas, quad)
        if got != mid:
            ng += 1
            print("NG", mid, rot, got)
print("done, NG =", ng)