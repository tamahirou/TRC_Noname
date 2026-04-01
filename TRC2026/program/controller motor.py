"""
【コントローラー側】送信プログラム
Wio-E5: UART0 / GP0(TX), GP1(RX)
SW1=GP2(前進) SW2=GP3(左旋回) SW3=GP4(後進) SW4=GP5(右旋回)
"""
from machine import UART, Pin
import time

# ===== LoRa UART =====
lora = UART(0, 9600)
lora.init(9600, bits=8, parity=None, stop=1, tx=Pin(0), rx=Pin(1))

# ===== ボタン =====
SW1 = Pin(2, Pin.IN)
SW2 = Pin(3, Pin.IN)
SW3 = Pin(4, Pin.IN)
SW4 = Pin(5, Pin.IN)

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

def send_packet(message):
    hex_str = message.encode().hex().upper()
    cmd = 'AT+TEST=TXLRPKT,"' + hex_str + '"'
    lora.write(cmd + "\r\n")
    # ★ wait_timeを0.5秒に短縮（長押し対応）
    time.sleep(0.5)
    response = ""
    while lora.any():
        data = lora.read()
        try:
            response += data.decode()
        except:
            pass
    ok = "TX DONE" in response or "+TEST: TX" in response
    return ok

# ===== 初期化 =====
print("=== コントローラー起動 ===")
time.sleep(1)
send_command("AT")
send_command("AT+MODE=TEST")
r = send_command("AT+TEST=RFCFG,923,7,0,1,8,14", 1.5)
if "ERROR" in r:
    print("再試行...")
    time.sleep(1)
    send_command("AT+TEST=RFCFG,923,7,0,1,8,14", 1.5)
print("=== 送信開始 ===")
print("SW1=前進 SW2=左旋回 SW3=後進 SW4=右旋回\n")

# ===== メインループ =====
LABELS = {"M:FWD":"前進","M:BCK":"後進","M:LFT":"左旋回","M:RGT":"右旋回","M:STP":"停止"}
last_cmd = None
tx_count = 0

while True:
    try:
        if   SW1.value() == 1: cmd = "M:FWD"
        elif SW2.value() == 1: cmd = "M:LFT"
        elif SW3.value() == 1: cmd = "M:BCK"
        elif SW4.value() == 1: cmd = "M:RGT"
        else:                  cmd = "M:STP"

        # コマンドが変化 or 押し続けている（停止以外）→ 送信
        if cmd != last_cmd or cmd != "M:STP":
            tx_count += 1
            ok = send_packet(cmd)
            print("[TX#" + str(tx_count) + "] " + LABELS[cmd] + (" ✓" if ok else " ✗"))
            last_cmd = cmd

        time.sleep(0.05)

    except KeyboardInterrupt:
        send_packet("M:STP")
        print("\n停止")
        break
    except Exception as e:
        print("エラー: " + str(e))
        import sys
        sys.print_exception(e)

