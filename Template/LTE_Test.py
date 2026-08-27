# Raspberry Pi Pico: USB <-> I2C-UART変換アダプタ SC16IS740 (Grove I2C, GP2=SDA, GP3=SCL)
# 水晶発振子: 7.3728MHz / FIFO: 64byte
# + AT / AT+QPING 送信 (MicroPython版)

from machine import I2C, Pin
import sys
import select
import time

# ---------- I2C 設定 ----------
I2C_ID = 1
I2C_SDA_PIN = 2
I2C_SCL_PIN = 3
I2C_FREQ = 400000

# 基板のアドレス設定(A0/A1ジャンパ等)に合わせて変更してください
SC16IS740_ADDR = 0x4D

UART_BAUDRATE = 115200
XTAL_FREQ = 7372800  # 7.3728MHz水晶発振子

# ---------- SC16IS740 レジスタ定義 ----------
REG_RHR = 0x00
REG_THR = 0x00
REG_IER = 0x01
REG_FCR = 0x02
REG_IIR = 0x02
REG_LCR = 0x03
REG_MCR = 0x04
REG_LSR = 0x05
REG_TXLVL = 0x08
REG_RXLVL = 0x09
REG_DLL = 0x00
REG_DLH = 0x01

LSR_RX_READY = 0x01
LSR_THR_EMPTY = 0x20

i2c = I2C(I2C_ID, sda=Pin(I2C_SDA_PIN), scl=Pin(I2C_SCL_PIN), freq=I2C_FREQ)


def reg_write(reg, val):
    i2c.writeto(SC16IS740_ADDR, bytes([reg << 3, val & 0xFF]))


def reg_read(reg):
    i2c.writeto(SC16IS740_ADDR, bytes([reg << 3]))
    return i2c.readfrom(SC16IS740_ADDR, 1)[0]


def uart_bridge_init(baudrate):
    divisor = XTAL_FREQ // (baudrate * 16)

    lcr = reg_read(REG_LCR)
    reg_write(REG_LCR, lcr | 0x80)          # DLAB=1: ボーレート分周レジスタへアクセス許可
    reg_write(REG_DLL, divisor & 0xFF)
    reg_write(REG_DLH, (divisor >> 8) & 0xFF)

    reg_write(REG_LCR, 0x03)                # 8bit, no parity, 1 stop, DLAB=0
    reg_write(REG_FCR, 0x07)                # FIFO(64byte)有効化&リセット
    reg_write(REG_IER, 0x00)                # 割込みは使わずポーリング運用

    actual_baud = XTAL_FREQ // (16 * divisor)
    print("Baudrate set: target={}, actual={}".format(baudrate, actual_baud))


def i2cuart_write(data):
    for b in data:
        while not (reg_read(REG_LSR) & LSR_THR_EMPTY):
            pass
        reg_write(REG_THR, b)


def i2cuart_any():
    return reg_read(REG_RXLVL)


def i2cuart_read():
    n = i2cuart_any()
    data = bytearray()
    for _ in range(n):
        data.append(reg_read(REG_RHR))
    return bytes(data)


# ---------- USB(stdin)ノンブロッキング読み取り ----------
poll = select.poll()
poll.register(sys.stdin, select.POLLIN)


def send_at(cmd, wait_ms=1000):
    """ATコマンドを送信し、一定時間レスポンスを受信して表示する"""
    print(">> {}".format(cmd))
    i2cuart_write((cmd + "\r\n").encode())

    start = time.ticks_ms()
    resp = b""
    while time.ticks_diff(time.ticks_ms(), start) < wait_ms:
        if i2cuart_any():
            resp += i2cuart_read()
        time.sleep_ms(10)

    if resp:
        try:
            print("<< {}".format(resp.decode()))
        except UnicodeError:
            print("<< {}".format(resp))
    else:
        print("<< (no response)")


# ---------- 初期化 ----------
uart_bridge_init(UART_BAUDRATE)
print("USB <-> I2C-UART (SC16IS740, Grove) bridge start")

time.sleep(2)
send_at("AT", wait_ms=1000)
send_at('AT+QPING=1,"8.8.8.8"', wait_ms=5000)

print("Enter bridge mode")

# ---------- ブリッジループ ----------
while True:
    while poll.poll(0):
        c = sys.stdin.read(1)
        if c:
            i2cuart_write(c.encode())

    if i2cuart_any():
        data = i2cuart_read()
        if data:
            sys.stdout.buffer.write(data)
