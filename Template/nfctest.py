# PN532 カードリーダー - Raspberry Pi Pico / MicroPython
# I2C0:  SDA=GP0  SCL=GP1
import time
from machine import I2C, Pin
from PN532 import PN532_I2C

# --- PN532 ---
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)
print("scan:", [hex(a) for a in i2c.scan()])   # 0x24 が出れば配線OK

pn = PN532_I2C(i2c, debug=False)
print("firmware:", list(pn.firmware_version()))
pn.set_mode()

print("カードをかざしてください...")

try:
    while True:
        target = pn.list_passive_target(timeout=1000)
        if target:
            tg, sens_res, sel_res, uid = target
            print("UID:", [hex(b) for b in uid])
            time.sleep_ms(300)      # 連続読み取り防止
except KeyboardInterrupt:
    print("終了")