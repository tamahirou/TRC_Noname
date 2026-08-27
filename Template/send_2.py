# send.py

import struct
import setting

def send(uart):
    # 今は transparent mode を前提にする
    # fixed_mode を使いたい場合は後で分岐追加する

    text = input("Send text> ")
    # UTF-8 でエンコード（ASCIIだけなら 'ascii' でもOK）
    payload = text.encode("utf-8")

    # 長さ制限（payload_length を超えたら切る）
    max_len = int(setting.payload_length)
    if len(payload) > max_len:
        payload = payload[:max_len]

    print("payload: {0}".format(payload))

    for data in payload:
        bdata = struct.pack("B", data)
        uart.write(bytes(bdata))

    print("SENT\n")
    return