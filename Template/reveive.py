# recieve.py（typoだけどファイル名そのままでOK）

import struct
import setting

def recv(uart):
    print("receive waiting...")
    payload = bytes()
    while True:
        count = uart.any()
        if count != 0:
            payload = payload + uart.read()
        elif count == 0 and len(payload) != 0:
            if setting.Argrssi:
                rssi = int(payload[-1]) - 256
                data = payload[:-1]  # 最後の1バイトはRSSI
                print("RECEIVED")
                print("raw:", payload)
                try:
                    text = data.decode("utf-8")
                    print("text:", text)
                except UnicodeDecodeError:
                    print("decode error")
                print("RSSI: {0} dBm".format(rssi))
                break
            else:
                print("RECEIVED")
                print("raw:", payload)
                try:
                    text = payload.decode("utf-8")
                    print("text:", text)
                except UnicodeDecodeError:
                    print("decode error")
                break
    print("\n")