"""
【機体側 Pico】LoRa受信 → モーター制御
=== ピン設定 ===
Wio-E5  : UART1 / GP4(TX), GP5(RX)
モーターA: AIN1=GP0, AIN2=GP1
モーターB: BIN1=GP2, BIN2=GP3
"""
from machine import UART, Pin
import time

# ===== ピン設定 =====
LORA_TX  = 4
LORA_RX  = 5
AIN1_PIN = 0
AIN2_PIN = 1
BIN1_PIN = 2
BIN2_PIN = 3
TIMEOUT_SEC = 2

# ===== LoRa UART =====
lora = UART(1, 9600)
lora.init(9600, bits=8, parity=None, stop=1, tx=Pin(LORA_TX), rx=Pin(LORA_RX))

# ===== DCモーター =====
AIN1 = Pin(AIN1_PIN, Pin.OUT)
AIN2 = Pin(AIN2_PIN, Pin.OUT)
BIN1 = Pin(BIN1_PIN, Pin.OUT)
BIN2 = Pin(BIN2_PIN, Pin.OUT)

def forward():
    """両モーター前進"""
    AIN1.value(1); AIN2.value(0)
    BIN1.value(0); BIN2.value(1)

def backward():
    """両モーター後進"""
    AIN1.value(0); AIN2.value(1)
    BIN1.value(1); BIN2.value(0)

def turn_left():
    """左旋回：Aモーターのみ"""
    AIN1.value(1); AIN2.value(0)   # Aのみ前進
    BIN1.value(0); BIN2.value(0)   # Bは停止

def turn_right():
    """右旋回：Bモーターのみ"""
    AIN1.value(0); AIN2.value(0)   # Aは停止
    BIN1.value(0); BIN2.value(1)   # Bのみ前進

def all_stop():
    AIN1.value(0); AIN2.value(0)
    BIN1.value(0); BIN2.value(0)

ACTIONS = {
    "M:FWD": (forward,     "前進"),
    "M:BCK": (backward,    "後進"),
    "M:LFT": (turn_left,   "左旋回(Aのみ)"),
    "M:RGT": (turn_right,  "右旋回(Bのみ)"),
    "M:STP": (all_stop,    "停止"),
}

def send_command(cmd, wait_time=1):
    lora.write(cmd + "\r\n")
    time.sleep(wait_time)
    response = ""
    while lora.any():
        data = lora.read()
        try:
            response += data.decode()
        except:
            pass
    print("CMD: " + cmd + " -> " + response.strip())
    return response.strip()

def restart_rx():
    lora.write("AT+TEST=RXLRPKT\r\n")
    time.sleep(0.3)
    while lora.any():
        lora.read()

def check_received():
    if lora.any():
        data = lora.read()
        try:
            response = data.decode()
        except:
            return None
        if "+TEST: RX" in response:
            try:
                start = response.find('"')
                if start != -1:
                    start += 1
                    end = response.find('"', start)
                    if end != -1:
                        return bytes.fromhex(response[start:end]).decode()
            except Exception as e:
                print("解析エラー: " + str(e))
    return None

# ===== 初期化 =====
print("=== 機体側起動 (Pico) ===")
all_stop()
time.sleep(1)
send_command("AT")
send_command("AT+MODE=TEST")
send_command("AT+TEST=RFCFG,923,7,0,1,8,14", 0.5)
send_command("AT+TEST=RXLRPKT")
print("=== 受信待機中 ===\n")

# ===== メインループ =====
rx_count     = 0
last_rx_time = time.time()

while True:
    try:
        msg = check_received()

        if msg:
            msg = msg.strip()
            last_rx_time = time.time()
            rx_count += 1
            if msg in ACTIONS:
                action, label = ACTIONS[msg]
                action()
                print("[RX#" + str(rx_count) + "] " + label)
            else:
                print("[RX#" + str(rx_count) + "] 不明: " + msg)
            restart_rx()

        if time.time() - last_rx_time > TIMEOUT_SEC:
            all_stop()
            last_rx_time = time.time()
            print("[タイムアウト] 停止")

        time.sleep(0.05)

    except KeyboardInterrupt:
        all_stop()
        print("\n終了")
        break
    except Exception as e:
        print("エラー: " + str(e))
        all_stop()
        import sys
        sys.print_exception(e)
