from machine import UART, Pin, PWM
import time

# ===== ピン設定 =====
LORA_TX  = 4
LORA_RX  = 5
AIN1_PIN = 0
AIN2_PIN = 1
BIN1_PIN = 2
BIN2_PIN = 3
TIMEOUT_SEC = 2

# ===== 速度設定（0〜65535）=====
SPEED      = 65535
TURN_SPEED = 10000

# ===== LoRa UART =====
lora = UART(1, 9600)
lora.init(9600, bits=8, parity=None, stop=1, tx=Pin(LORA_TX), rx=Pin(LORA_RX))

# ===== PWMモーター =====
AIN1 = PWM(Pin(AIN1_PIN)); AIN1.freq(1000)
AIN2 = PWM(Pin(AIN2_PIN)); AIN2.freq(1000)
BIN1 = PWM(Pin(BIN1_PIN)); BIN1.freq(1000)
BIN2 = PWM(Pin(BIN2_PIN)); BIN2.freq(1000)

# ★ 全ピンをまとめて設定するヘルパー（書き忘れ防止）

"""モーター"""
AIN1 = PWM(Pin(2))
AIN2 = PWM(Pin(3))
BIN1 = PWM(Pin(1))
BIN2 = PWM(Pin(0))

AIN1.freq(20000)
AIN2.freq(20000)
BIN1.freq(20000)
BIN2.freq(20000)

def left_forward(speed):
    AIN1.duty_u16(0)
    AIN2.duty_u16(speed)

def left_backward(speed):
    AIN1.duty_u16(speed)
    AIN2.duty_u16(0)

def left_stop():
    AIN1.duty_u16(0)
    AIN2.duty_u16(0)


def right_forward(speed):
    BIN1.duty_u16(65535 - speed)
    BIN2.duty_u16(0)

def right_backward(speed):
    BIN1.duty_u16(65535)
    BIN2.duty_u16(65535)

def right_stop():
    BIN1.duty_u16(0)
    BIN2.duty_u16(0)


def motor_stop():
    left_stop()
    right_stop()

def motor_forward(speed):
    left_forward(speed)
    right_forward(speed)

def motor_backward(speed):
    left_backward(speed)
    right_backward(speed)
    
def _set(a1, a2, b1, b2):
    AIN1.duty_u16(a1)
    AIN2.duty_u16(a2)
    BIN1.duty_u16(65535 - b1)
    BIN2.duty_u16(b2 - 65535)

def forward():
    motor_forward(65535)

def backward():
    motor_backward(65535)

def turn_left():
    left_forward(10000)
    right_forward(65535)# Aのみ、Bは必ず0

def turn_right():
    left_forward(65535)
    right_forward(10000)   # Bのみ、Aは必ず0

def all_stop():
    motor_forward(0)

ACTIONS = {
    "M:FWD": (forward,    "前進"),
    "M:BCK": (backward,   "後進"),
    "M:LFT": (turn_left,  "左旋回(Aのみ)"),
    "M:RGT": (turn_right, "右旋回(Bのみ)"),
    "M:STP": (all_stop,   "停止"),
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
print("=== 機体側起動 (Pico / PWM) ===")
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

