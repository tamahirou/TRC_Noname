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

# \r\n をまたいで届いたデータをつなげるための受信バッファ
rxbuf = b""

def nmea_to_decimal(raw, hemi):
    """ddmm.mmmm (または dddmm.mmmm) 形式を10進度に変換する"""
    dot = raw.find(".")
    deg_len = dot - 2
    deg = int(raw[:deg_len])
    minutes = float(raw[deg_len:])
    dec = deg + minutes / 60.0
    if hemi in ("S", "W"):
        dec = -dec
    return dec

def parse_gga(line):
    """$..GGA 文から時刻・緯度・経度・高度・衛星数を取り出す。Fixなしなら None"""
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

def feed(data):
    """受信データをバッファに追加し、GGA文から座標を取り出して表示する"""
    global rxbuf
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
