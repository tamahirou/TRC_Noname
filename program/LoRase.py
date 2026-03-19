from machine import UART, Pin
import time

# LoRa UART設定
uart = UART(0, 9600)
uart.init(9600, bits=8, parity=None, stop=1, tx=Pin(0), rx=Pin(1))

# 送信間隔（秒）
LORA_TX_INTERVAL = 5

# ===== 送信メッセージをここに書く =====
MESSAGE = "Hello LoRa!"
# =====================================

def send_command(cmd, wait_time=1):
    """ATコマンド送信"""
    uart.write(cmd + "\r\n")
    time.sleep(wait_time)
    response = ""
    while uart.any():
        data = uart.read()
        try:
            response += data.decode()
        except:
            pass
    print("CMD: " + cmd + " -> " + response.strip())
    return response.strip()

def send_packet(message):
    """文字列をHEXに変換して送信"""
    hex_str = message.encode().hex().upper()
    cmd = 'AT+TEST=TXLRPKT,"' + hex_str + '"'
    response = send_command(cmd, wait_time=2)
    if "TX DONE" in response or "+TEST: TX" in response:
        return True
    return False

# ===== 初期化 =====
print("=== LoRa送信機 ===\n")
time.sleep(1)
print("初期化中...")
print("\n--- 設定開始 ---")
send_command("AT")
send_command("AT+MODE=TEST")
send_command("AT+TEST=RFCFG,923,7,0,1,8,14", 0.5)
print("--- 設定完了 ---\n")

# ===== メインループ =====
print("=== 送信開始 ===")
print("メッセージ: " + MESSAGE)
print("送信間隔: " + str(LORA_TX_INTERVAL) + "秒\n")

packet_count = 0
last_tx_time = 0

while True:
    try:
        current_time = time.time()
        if current_time - last_tx_time >= LORA_TX_INTERVAL:
            packet_count += 1
            print("[TX #" + str(packet_count) + "] 送信: " + MESSAGE)
            ok = send_packet(MESSAGE)
            if ok:
                print("    -> 送信完了")
            else:
                print("    -> 送信失敗")
            print()
            last_tx_time = current_time
        time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n送信機停止")
        uart.write("AT+TEST=STOP\r\n")
        break
    except Exception as e:
        print("エラー: " + str(e))
        import sys
        sys.print_exception(e)


