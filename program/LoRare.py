from machine import UART, Pin
import time

# LoRa UART設定（送信側と完全一致）
uart = UART(1, 9600)
uart.init(9600, bits=8, parity=None, stop=1, tx=Pin(4), rx=Pin(5))

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

def check_received():
    """受信データ確認"""
    if uart.any():
        data = uart.read()
        try:
            response = data.decode()
        except:
            return None, None

        if "+TEST: RX" in response:
            try:
                start = response.find('"')
                if start != -1:
                    start += 1
                    end = response.find('"', start)
                    if end != -1:
                        hex_data = response[start:end]
                        msg = bytes.fromhex(hex_data).decode()

                        rssi = "N/A"
                        if "RSSI" in response:
                            rssi_start = response.find("RSSI") + 4
                            rssi_end = response.find(",", rssi_start)
                            if rssi_end == -1:
                                rssi_end = response.find("\r", rssi_start)
                            if rssi_end != -1:
                                rssi = response[rssi_start:rssi_end].strip()

                        return msg, rssi
            except Exception as e:
                print("解析エラー: " + str(e))
                print("生データ: " + response)

    return None, None

# ===== 初期化（送信側のsetup()と完全一致）=====
print("=== LoRa受信機 ===\n")
time.sleep(1)
print("初期化中...")
print("\n--- 設定開始 ---")
send_command("AT")
send_command("AT+MODE=TEST")
send_command("AT+TEST=RFCFG,923,7,0,1,8,14", 0.5)  # ★送信側と完全一致
send_command("AT+TEST=RXLRPKT")
print("--- 設定完了 ---\n")

# ===== メインループ =====
print("=== 受信待機中 ===")
print("Ctrl+C で停止\n")

receive_count = 0

while True:
    try:
        msg, rssi = check_received()

        if msg:
            receive_count += 1
            print("[" + str(receive_count) + "] 受信: " + msg)
            if rssi != "N/A":
                print("    RSSI: " + rssi + " dBm")
            print()

        time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n受信機停止")
        uart.write("AT+TEST=STOP\r\n")
        break
    except Exception as e:
        print("エラー: " + str(e))
        import sys
        sys.print_exception(e)

