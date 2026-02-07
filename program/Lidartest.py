

from machine import UART, Pin, PWM
import time

KYORI = 500

uart = UART(0, baudrate=115200, tx=Pin(12), rx=Pin(13))


def angle_to_duty(angle):
    duty = int(65535 * (2.5 + (angle * 9.5 / 180)) / 100)
    return duty

print("デバッグモード開始...")
print("UART設定:", uart)


print("LiDARからのデータを待機中...")

# LiDARのデータを確認
for i in range(50):  # 5秒間データを確認
    if uart.any():
        data = uart.read()
        print(f"受信データ: {data}")
        print(f"データ長: {len(data)}")
        print(f"16進数: {[hex(b) for b in data]}")
    else:
        print(".", end="")
    time.sleep(0.1)

print("\nデバッグ終了")