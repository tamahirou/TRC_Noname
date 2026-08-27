# gnss_reader.py
# Raspberry Pi Pico: GP2=SDA, GP3=SCL の SoftI2C で GNSS モジュールを読むための共通モジュール。
# 他のプログラム(BG96/MQTT送信版など)からは import gnss_reader して使う。
#
# 使い方:
#   import gnss_reader as gnss
#
#   i2c = gnss.init()                # CE ON->OFF切替 + SoftI2C初期化(再生成込み)
#   reader = gnss.GNSSReader(i2c)
#
#   def on_line(text):
#       fix = gnss.parse_gga(text)
#       if fix:
#           time_s, lat, lon, alt, num_sat = fix
#           ...
#
#   while True:
#       reader.poll(on_line)
#       time.sleep_ms(300)

from machine import Pin, SoftI2C
import time, struct

# ============================================================
# ピン / I2C設定
# ============================================================
I2C_SDA, I2C_SCL, I2C_FREQ = 2, 3, 100000
CE_PIN = 2  # 注意: SDAと同じGP2を使用(CE制御時はSoftI2Cのピン設定が一時的に上書きされる)

# ============================================================
# GNSSモジュールのレジスタ/コマンド定義
# ============================================================
ADDR_CR_CW, ADDR_R = 0x50, 0x54
CR_CMD, CMD_LEN, RX_LEN = 0xAA51, 8, 4
TX_LEN_REG_OFFSET, TX_BUF_REG_OFFSET = 0x0008, 0x2000

CMD_GAP_MS = 30
MAX_CONSEC_FAIL = 2  # 長時間ポーリングが空くとGNSS側がスリープ/リセットされるため、早めにバス再初期化する


def make_i2c():
    """SoftI2Cを(再)生成する。CEピン操作でGP2の設定が上書きされた後は必ずこれで作り直すこと。"""
    return SoftI2C(sda=Pin(I2C_SDA, Pin.PULL_UP), scl=Pin(I2C_SCL, Pin.PULL_UP), freq=I2C_FREQ)


def make_cmd(off, cmd, length):
    b = bytearray(CMD_LEN)
    b[0] = off & 0xFF;    b[1] = (off >> 8) & 0xFF
    b[2] = cmd & 0xFF;    b[3] = (cmd >> 8) & 0xFF
    b[4] = length & 0xFF; b[5] = (length >> 8) & 0xFF
    b[6] = (length >> 16) & 0xFF; b[7] = (length >> 24) & 0xFF
    return bytes(b)


def power_cycle_ce(low_ms=1000, high_ms=1000):
    """GNSSモジュールのCEをLow->Highに切り替えて起動する。"""
    ce = Pin(CE_PIN, Pin.OUT, value=0)
    time.sleep_ms(low_ms)
    ce.value(1)
    time.sleep_ms(high_ms)


def init(low_ms=1000, high_ms=1000, settle_ms=1000):
    """CE起動 + SoftI2C初期化(再生成込み)を行い、使えるi2cオブジェクトを返す。

    重要: CE操作でGP2(=SDA)のピン設定が上書きされるため、
    CE操作後は必ずSoftI2Cを作り直す(doc1側の挙動に合わせている)。
    """
    power_cycle_ce(low_ms, high_ms)
    i2c = make_i2c()
    time.sleep_ms(settle_ms)
    return i2c


def resync(i2c=None):
    """長時間I2Cアクセスが空いた後(例: BG96のAT初期化中)にGNSS側が
    スリープ/内部リセットして最初の1回だけENODEVになるケースがあるため、
    メインループに入る直前に呼んでバスを作り直しておく。
    """
    new_i2c = make_i2c()
    time.sleep_ms(200)
    return new_i2c


# ============================================================
# NMEA (GGA) パース
# ============================================================
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
    """$..GGA行をパースして (time_s, lat, lon, alt, num_sat) を返す。Fixなしや非GGA行はNoneを返す。"""
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


# ============================================================
# GNSS読み取りクラス
# ============================================================
class GNSSReader:
    """1回のpoll()呼び出しで1サイクル分のI2C読み取りを行い、
    \\r\\nで区切られた行が確定するたびに on_line(text) コールバックを呼ぶ。
    """

    def __init__(self, i2c):
        self.i2c = i2c
        self.rxbuf = b""
        self.fail_count = 0

    def poll(self, on_line=None):
        try:
            self.i2c.writeto(ADDR_CR_CW, make_cmd(TX_LEN_REG_OFFSET, CR_CMD, RX_LEN))
            time.sleep_ms(CMD_GAP_MS)
            n = struct.unpack("<I", self.i2c.readfrom(ADDR_R, RX_LEN))[0]
            if n == 0:
                self.fail_count = 0
                return
            if n > 255:
                n = 255
            time.sleep_ms(CMD_GAP_MS)
            self.i2c.writeto(ADDR_CR_CW, make_cmd(TX_BUF_REG_OFFSET, CR_CMD, n))
            time.sleep_ms(CMD_GAP_MS)
            data = self.i2c.readfrom(ADDR_R, n)
            self._feed(data, on_line)
            self.fail_count = 0
        except OSError as e:
            self.fail_count += 1
            print("I2C error (%d回連続):" % self.fail_count, e)
            if self.fail_count >= MAX_CONSEC_FAIL:
                print("バスをリセットします")
                self.i2c = make_i2c()
                self.fail_count = 0
                time.sleep_ms(200)

    def _feed(self, data, on_line):
        self.rxbuf += data
        while True:
            idx = self.rxbuf.find(b"\r\n")
            if idx == -1:
                break
            line = self.rxbuf[:idx]
            self.rxbuf = self.rxbuf[idx + 2:]
            if not line:
                continue
            try:
                text = line.decode()
            except UnicodeError:
                continue
            if on_line:
                on_line(text)


# ============================================================
# このファイル単体で実行した場合(動作確認用): 生の行を表示するだけ
# ============================================================
if __name__ == "__main__":
    i2c = init()
    print("I2C scan:", [hex(a) for a in i2c.scan()])
    reader = GNSSReader(i2c)

    def _print_line(text):
        print(text)

    while True:
        reader.poll(_print_line)
        time.sleep_ms(300)