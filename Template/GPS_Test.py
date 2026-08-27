# Raspberry Pi Pico: GNSS(I2C0: GP0/GP1) + BG96(I2C1: GP2/GP3, SC16IS740経由)
# 位置情報がFixしたらMQTTでLTE経由送信する

from machine import Pin, SoftI2C, I2C
import time, struct, sys

# ============================================================
# GNSS側 (I2C0: GP0=SDA, GP1=SCL)
# ============================================================
CE = Pin(29, Pin.OUT, value=0)  # ※GNSSモジュールのCEピン。BG96側のGP2(SDA)と重複しないか要確認
ADDR_CR_CW, ADDR_R = 0x50, 0x54
CR_CMD, CMD_LEN, RX_LEN = 0xAA51, 8, 4
TX_LEN_REG_OFFSET, TX_BUF_REG_OFFSET = 0x0008, 0x2000
GNSS_SDA, GNSS_SCL, GNSS_I2C_FREQ = 2, 3, 100000


def make_gnss_i2c():
    return SoftI2C(sda=Pin(GNSS_SDA, Pin.PULL_UP), scl=Pin(GNSS_SCL, Pin.PULL_UP), freq=GNSS_I2C_FREQ)


gnss_i2c = make_gnss_i2c()


def make_cmd(off, cmd, length):
    b = bytearray(CMD_LEN)
    b[0] = off & 0xFF; b[1] = (off >> 8) & 0xFF
    b[2] = cmd & 0xFF; b[3] = (cmd >> 8) & 0xFF
    b[4] = length & 0xFF; b[5] = (length >> 8) & 0xFF
    b[6] = (length >> 16) & 0xFF; b[7] = (length >> 24) & 0xFF
    return bytes(b)


CSV_PATH = "gnss_log.csv"


def open_csv():
    try:
        open(CSV_PATH, "r").close()
        is_new = False
    except OSError:
        is_new = True
    f = open(CSV_PATH, "a")
    if is_new:
        f.write("time,lat,lon,alt,num_sat\n")
        f.flush()
    return f


csv_file = open_csv()
rxbuf = b""


def nmea_to_decimal(raw, hemi):
    dot = raw.find(".")
    deg_len = dot - 2
    deg = int(raw[:deg_len])
    minutes = float(raw[deg_len:])
    dec = deg + minutes / 60.0
    if hemi in ("S", "W"):
        dec = -dec
    return dec


def parse_gga(line):
    if len(line) < 6 or line[0:1] != "$" or line[3:6] != "GGA":
        return None
    body = line.split("*")[0]
    p = body.split(",")
    if len(p) < 10:
        return None
    time_s, lat_raw, ns, lon_raw, ew, fix_q, num_sat, _hdop, alt = p[1:10]
    if not lat_raw or not lon_raw or fix_q == "0":
        return None
    lat = nmea_to_decimal(lat_raw, ns)
    lon = nmea_to_decimal(lon_raw, ew)
    return time_s, lat, lon, alt, num_sat


# MQTT送信間隔の制御用(GPSは高頻度で更新されるので間引く)
MQTT_SEND_INTERVAL_MS = 15000
last_mqtt_send = 0


def feed(data):
    """受信データをバッファに追加し、GGA文から座標を取り出して表示・保存・MQTT送信する"""
    global rxbuf, last_mqtt_send
    rxbuf += data
    while True:
        idx = rxbuf.find(b"\r\n")
        if idx == -1:
            break
        line = rxbuf[:idx]
        rxbuf = rxbuf[idx + 2:]
        if not line:
            continue
        try:
            text = line.decode()
        except UnicodeError:
            continue
        fix = parse_gga(text)
        if fix:
            time_s, lat, lon, alt, num_sat = fix
            print("%s 緯度=%f 経度=%f 高度=%sm 衛星数=%s" % (time_s, lat, lon, alt, num_sat))
            csv_file.write("%s,%f,%f,%s,%s\n" % (time_s, lat, lon, alt, num_sat))
            csv_file.flush()

            # 一定間隔でMQTT送信(GPSは頻繁に更新されるため間引く)
            now = time.ticks_ms()
            if mqtt_ready and time.ticks_diff(now, last_mqtt_send) > MQTT_SEND_INTERVAL_MS:
                msg = "time=%s,lat=%f,lon=%f,alt=%s,sat=%s" % (time_s, lat, lon, alt, num_sat)
                mqtt_publish(msg)
                last_mqtt_send = now


# ============================================================
# BG96側 (I2C1: GP2=SDA, GP3=SCL, SC16IS740経由)
# ============================================================
BG_I2C_ID = 1
BG_SDA_PIN = 2
BG_SCL_PIN = 3
BG_I2C_FREQ = 400000
SC16IS740_ADDR = 0x4D  # 実機のアドレスに合わせて変更(要 i2c.scan() 確認)

UART_BAUDRATE = 115200
XTAL_FREQ = 7372800  # 7.3728MHz水晶発振子

REG_RHR = 0x00
REG_THR = 0x00
REG_IER = 0x01
REG_FCR = 0x02
REG_LCR = 0x03
REG_LSR = 0x05
REG_RXLVL = 0x09
REG_DLL = 0x00
REG_DLH = 0x01
LSR_THR_EMPTY = 0x20

bg_i2c = I2C(BG_I2C_ID, sda=Pin(BG_SDA_PIN), scl=Pin(BG_SCL_PIN), freq=BG_I2C_FREQ)


def reg_write(reg, val):
    bg_i2c.writeto(SC16IS740_ADDR, bytes([reg << 3, val & 0xFF]))


def reg_read(reg):
    bg_i2c.writeto(SC16IS740_ADDR, bytes([reg << 3]))
    return bg_i2c.readfrom(SC16IS740_ADDR, 1)[0]


def uart_bridge_init(baudrate):
    divisor = XTAL_FREQ // (baudrate * 16)
    lcr = reg_read(REG_LCR)
    reg_write(REG_LCR, lcr | 0x80)
    reg_write(REG_DLL, divisor & 0xFF)
    reg_write(REG_DLH, (divisor >> 8) & 0xFF)
    reg_write(REG_LCR, 0x03)
    reg_write(REG_FCR, 0x07)
    reg_write(REG_IER, 0x00)
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


def send_at(cmd, wait_ms=1000, echo=True):
    if echo:
        print(">> {}".format(cmd))
    i2cuart_write((cmd + "\r\n").encode())
    start = time.ticks_ms()
    resp = b""
    while time.ticks_diff(time.ticks_ms(), start) < wait_ms:
        if i2cuart_any():
            resp += i2cuart_read()
        time.sleep_ms(10)
    text = ""
    try:
        text = resp.decode()
    except UnicodeError:
        text = str(resp)
    if echo and text:
        print("<< {}".format(text))
    return text


def read_more(wait_ms=3000, label="URC"):
    start = time.ticks_ms()
    resp = b""
    while time.ticks_diff(time.ticks_ms(), start) < wait_ms:
        if i2cuart_any():
            resp += i2cuart_read()
        time.sleep_ms(10)
    if resp:
        try:
            text = resp.decode()
        except UnicodeError:
            text = str(resp)
        print("<< ({}) {}".format(label, text))
        return text
    return ""


# APN設定 (CALENDAR SIM実機で成功した値)
APN = "ppsim.jp"
AUTH_PATTERNS = [
    ("pp@sim", "jpn", 3, "PAP/CHAP auto"),
    ("pp@sim", "jpn", 1, "PAP"),
    ("pp@sim", "jpn", 2, "CHAP"),
    ("", "", 0, "NONE (no auth)"),
]

MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "pico_bg96_gnss001"   # 前回と被らない名前に変更推奨
MQTT_TOPIC = "pico_bg96_gnss001/data"
MQTT_CTX_ID = 1


def try_activate_pdp():
    for user, pw, auth, desc in AUTH_PATTERNS:
        print("=== Trying APN auth pattern: {} ===".format(desc))
        send_at("AT+QIDEACT=1", wait_ms=5000)
        send_at('AT+CGDCONT=1,"IP","{}"'.format(APN))
        if user:
            send_at('AT+QICSGP=1,1,"{}","{}","{}",{}'.format(APN, user, pw, auth))
        else:
            send_at('AT+QICSGP=1,1,"{}",0'.format(APN))
        result = send_at("AT+QIACT=1", wait_ms=10000)
        if "OK" in result:
            print("=== SUCCESS with pattern: {} ===".format(desc))
            send_at("AT+QIACT?")
            return True
        else:
            send_at("AT+QIGETERROR")
            print("--- Pattern failed: {} ---".format(desc))
    print("=== All APN auth patterns failed ===")
    return False


def setup_pdp_and_mqtt():
    send_at("AT")
    send_at("ATE0")
    send_at("AT+CPIN?")
    send_at("AT+CSQ")
    send_at("AT+CGREG?")
    send_at("AT+CEREG?")

    ok = try_activate_pdp()
    if not ok:
        print("!!! PDP activation failed on all patterns. Aborting MQTT setup. !!!")
        return False

    send_at('AT+QMTCFG="recv/mode",{},0,1'.format(MQTT_CTX_ID))
    send_at('AT+QMTOPEN={},"{}",{}'.format(MQTT_CTX_ID, MQTT_BROKER, MQTT_PORT), wait_ms=5000)
    read_more(wait_ms=5000, label="QMTOPEN URC")

    send_at('AT+QMTCONN={},"{}"'.format(MQTT_CTX_ID, MQTT_CLIENT_ID), wait_ms=8000)
    read_more(wait_ms=3000, label="QMTCONN URC")

    return True


def mqtt_publish(message, msg_id=0, qos=0):
    cmd = 'AT+QMTPUB={},{},{},0,"{}"'.format(MQTT_CTX_ID, msg_id, qos, MQTT_TOPIC)
    print(">> {}".format(cmd))
    i2cuart_write((cmd + "\r\n").encode())

    start = time.ticks_ms()
    resp = b""
    while time.ticks_diff(time.ticks_ms(), start) < 3000:
        if i2cuart_any():
            resp += i2cuart_read()
            if b">" in resp:
                break
        time.sleep_ms(10)

    if b">" not in resp:
        print("!!! No '>' prompt received. QMTPUB may have failed (not connected?). !!!")
        try:
            print("<< {}".format(resp.decode()))
        except UnicodeError:
            print("<< {}".format(resp))
        return

    i2cuart_write(message.encode())
    i2cuart_write(bytes([0x1A]))  # Ctrl+Z で確定

    start = time.ticks_ms()
    resp2 = b""
    while time.ticks_diff(time.ticks_ms(), start) < 5000:
        if i2cuart_any():
            resp2 += i2cuart_read()
        time.sleep_ms(10)

    try:
        print("<< {}".format(resp2.decode()))
    except UnicodeError:
        print("<< {}".format(resp2))


# ============================================================
# 初期化
# ============================================================
uart_bridge_init(UART_BAUDRATE)
print("BG96 setup start")
mqtt_ready = setup_pdp_and_mqtt()

if mqtt_ready:
    print("MQTT ready. Waiting for GNSS fix...")
else:
    print("MQTT setup failed. GNSS logging will continue without sending.")

CE.value(0)
time.sleep(1)
CE.value(1)
time.sleep(3)
print("gnss scan:", [hex(a) for a in gnss_i2c.scan()])

# ============================================================
# メインループ: GNSS読み取り → Fixが出たらMQTT送信
# ============================================================
CMD_GAP_MS = 30
MAX_CONSEC_FAIL = 5
fail_count = 0

while True:
    try:
        gnss_i2c.writeto(ADDR_CR_CW, make_cmd(TX_LEN_REG_OFFSET, CR_CMD, RX_LEN))
        time.sleep_ms(CMD_GAP_MS)
        n = struct.unpack("<I", gnss_i2c.readfrom(ADDR_R, RX_LEN))[0]
        if n == 0:
            print("(データなし)")
            fail_count = 0
            time.sleep_ms(300)
            continue
        if n > 255:
            n = 255
        time.sleep_ms(CMD_GAP_MS)
        gnss_i2c.writeto(ADDR_CR_CW, make_cmd(TX_BUF_REG_OFFSET, CR_CMD, n))
        time.sleep_ms(CMD_GAP_MS)
        data = gnss_i2c.readfrom(ADDR_R, n)
        feed(data)
        fail_count = 0
    except OSError as e:
        fail_count += 1
        print("I2C error (%d回連続):" % fail_count, e)
        if fail_count >= MAX_CONSEC_FAIL:
            print("バスをリセットします")
            gnss_i2c = make_gnss_i2c()
            fail_count = 0
            time.sleep_ms(200)
    time.sleep_ms(300)