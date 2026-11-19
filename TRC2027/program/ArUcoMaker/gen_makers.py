# gen_markers.py  (PCで実行 / opencv-contrib-python が必要)
# 使い方:
#   python gen_markers.py 0 5 123        -> ID 0,5,123 を生成
#   python gen_markers.py 0-9            -> ID 0〜9 を生成
#   python gen_markers.py 0-9 --cell 50 --margin 2 --label
# 出力: markers/aruco7x7_1000_id{ID}.png
import argparse, os
import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("ids", nargs="+", help="ID（例: 0 5 123 / 範囲 0-9）")
ap.add_argument("--cell", type=int, default=40, help="1マスのピクセル数（既定40 -> マーカー本体360px）")
ap.add_argument("--margin", type=int, default=2, help="周囲の白余白（マス数。1以上推奨）")
ap.add_argument("--label", action="store_true", help="余白部分にID番号を書き込む")
ap.add_argument("--out", default="markers", help="出力フォルダ")
args = ap.parse_args()

# ID展開
ids = []
for s in args.ids:
    if "-" in s:
        a, b = s.split("-")
        ids += list(range(int(a), int(b) + 1))
    else:
        ids.append(int(s))

for i in ids:
    if not 0 <= i < 1000:
        raise SystemExit("IDは0〜999です: %d" % i)

ar = cv2.aruco
dic = ar.getPredefinedDictionary(ar.DICT_7X7_1000)
gen = getattr(ar, "generateImageMarker", None) or getattr(ar, "drawMarker")

os.makedirs(args.out, exist_ok=True)
side = args.cell * 9            # 黒枠1マス + 7x7 + 黒枠1マス = 9マス
m = args.cell * args.margin

for mid in ids:
    img = np.asarray(gen(dic, mid, side, None, 1), dtype=np.uint8)
    canvas = np.full((side + 2 * m, side + 2 * m), 255, np.uint8)
    canvas[m:m + side, m:m + side] = img
    if args.label:
        cv2.putText(canvas, "ID %d" % mid, (4, canvas.shape[0] - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, 0, 1, cv2.LINE_AA)
    path = os.path.join(args.out, "aruco7x7_1000_id%d.png" % mid)
    cv2.imwrite(path, canvas)
    print("saved", path, canvas.shape)