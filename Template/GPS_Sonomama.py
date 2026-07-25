from machine import Pin, SoftI2C
import time, struct, sys

CE = Pin(2, Pin.OUT, value=0)
ADDR_CR_CW, ADDR_R = 0x50, 0x54
CR_CMD, CMD_LEN, RX_LEN = 0xAA51, 8, 4
TX_LEN_REG_OFFSET, TX_BUF_REG_OFFSET = 0x0008, 0x2000
I2C_SDA, I2C_SCL, I2C_FREQ = 2, 3, 100000

def make_i2c():
    return SoftI2C(sda=Pin(I2C_SDA, Pin.PULL_UP), scl=Pin(I2C_SCL, Pin.PULL_UP), freq=I2C_FREQ)

i2c = make_i2c()

CE.value(0)
time.sleep(1)
CE.value(1)
time.sleep(3)

print("scan:", [hex(a) for a in i2c.scan()])

def make_cmd(off, cmd, length):
    b = bytearray(CMD_LEN)
    b[0]=off&0xFF; b[1]=(off>>8)&0xFF
    b[2]=cmd&0xFF; b[3]=(cmd>>8)&0xFF
    b[4]=length&0xFF; b[5]=(length>>8)&0xFF
    b[6]=(length>>16)&0xFF; b[7]=(length>>24)&0xFF
    return bytes(b)

# \r\n をまたいで届いたデータをつなげるための受信バッファ
rxbuf = b""

def feed(data):
    """受信データをバッファに追加し、\\r\\n で区切れた行だけを表示する"""
    global rxbuf
    rxbuf += data
    while True:
        idx = rxbuf.find(b"\r\n")
        if idx == -1:
            break
        line = rxbuf[:idx]
        rxbuf = rxbuf[idx + 2:]
        if line:
            try:
                print(line.decode())
            except UnicodeError:
                print(line)

CMD_GAP_MS = 30       # 各I2Cコマンド間の待ち時間(10ms -> 30msに延長)
MAX_CONSEC_FAIL = 5   # これだけ連続失敗したらバスをリセットする

fail_count = 0

while True:
    try:
        i2c.writeto(ADDR_CR_CW, make_cmd(TX_LEN_REG_OFFSET, CR_CMD, RX_LEN))
        time.sleep_ms(CMD_GAP_MS)
        n = struct.unpack("<I", i2c.readfrom(ADDR_R, RX_LEN))[0]

        if n == 0:
            print("(データなし)")
            fail_count = 0
            time.sleep_ms(300)
            continue
        if n > 255:
            n = 255

        time.sleep_ms(CMD_GAP_MS)
        i2c.writeto(ADDR_CR_CW, make_cmd(TX_BUF_REG_OFFSET, CR_CMD, n))
        time.sleep_ms(CMD_GAP_MS)
        data = i2c.readfrom(ADDR_R, n)

        feed(data)
        fail_count = 0

    except OSError as e:
        fail_count += 1
        print("I2C error (%d回連続):" % fail_count, e)
        if fail_count >= MAX_CONSEC_FAIL:
            print("バスをリセットします")
            i2c = make_i2c()
            fail_count = 0
            time.sleep_ms(200)

    time.sleep_ms(300)

