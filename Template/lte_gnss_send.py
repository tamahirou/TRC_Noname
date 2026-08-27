# main_bg96_mqtt.py
# gnss_reader.py をimportし、GNSS読み取りロジックは共通モジュール側に一本化。
# ここではSC16IS740(BG96用UART変換)経由でのAT操作/MQTT送信のみを担当する。

from machine import Pin, SoftI2C
import time, struct

import gnss_reader as gnss

# ============================================================
# GNSSと同じSoftI2Cバスを共有する
# ============================================================
i2c = gnss.init()  # CE起動 + SoftI2C初期化(内部でGP2/GP3, 100kHzを使用)
print("I2C scan:", [hex(a) for a in i2c.scan()])

reader = gnss.GNSSReader(i2c)

# ============================================================
# CSVログ
# ============================================================
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

# ============================================================
# SC16IS740 (BG96用UART変換)
# ============================================================
SC16IS740_ADDR = 0x4D

UART_BAUDRATE = 115200
XTAL_FREQ = 7372800

REG_RHR   = 0x00
REG_THR   = 0x00
REG_IER   = 0x01
REG_FCR   = 0x02
REG_LCR   = 0x03
REG_LSR   = 0x05
REG_RXLVL = 0x09
REG_DLL   = 0x00
REG_DLH   = 0x01
LSR_THR_EMPTY = 0x20


def reg_write(reg, val):
    i2c.writeto(SC16IS740_ADDR, bytes([reg << 3, val & 0xFF]))


def reg_read(reg):
    i2c.writeto(SC16IS740_ADDR, bytes([reg << 3]))
    return i2c.readfrom(SC16IS740_ADDR, 1)[0]


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


APN = "ppsim.jp"
AUTH_PATTERNS = [
    ("pp@sim", "jpn", 3, "PAP/CHAP auto"),
    ("pp@sim", "jpn", 1, "PAP"),
    ("pp@sim", "jpn", 2, "CHAP"),
    ("", "", 0, "NONE (no auth)"),
]

MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "pico_bg96_gnss001"
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
        print("!!! PDP activation failed. Aborting MQTT setup. !!!")
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
        print("!!! No '>' prompt. QMTPUB failed. !!!")
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
print("BG96 MQTT setup start")
mqtt_ready = setup_pdp_and_mqtt()

if mqtt_ready:
    print("MQTT ready. Waiting for GNSS fix...")
else:
    print("MQTT setup failed. GNSS logging continues without sending.")

# BG96のAT初期化中(数秒〜数十秒)はGNSSに一切アクセスしていないため、
# GNSSモジュール側がスリープ/内部リセットしている可能性がある。
# メインループに入る前にバスを作り直しておき、1回目のENODEVを防ぐ。
i2c = gnss.resync(i2c)
reader.i2c = i2c

# ============================================================
# メインループ: GNSS読み取り(gnss_reader.py)-> Fixが出たらMQTT送信
# ============================================================
MQTT_SEND_INTERVAL_MS = 15000
last_mqtt_send = 0


def on_gnss_line(text):
    global last_mqtt_send
    fix = gnss.parse_gga(text)
    if not fix:
        return
    time_s, lat, lon, alt, num_sat = fix
    print("%s 緯度=%f 経度=%f 高度=%sm 衛星数=%s" % (time_s, lat, lon, alt, num_sat))
    csv_file.write("%s,%f,%f,%s,%s\n" % (time_s, lat, lon, alt, num_sat))
    csv_file.flush()
    now = time.ticks_ms()
    if mqtt_ready and time.ticks_diff(now, last_mqtt_send) > MQTT_SEND_INTERVAL_MS:
        msg = "time=%s,lat=%f,lon=%f,alt=%s,sat=%s" % (time_s, lat, lon, alt, num_sat)
        mqtt_publish(msg)
        last_mqtt_send = now


while True:
    reader.poll(on_gnss_line)
    time.sleep_ms(300)