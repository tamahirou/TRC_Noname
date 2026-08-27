import struct
import setting

def send(uart, text=None):
    if setting.fixed_mode:
        t_addr = int(setting.target_address)
        t_addr_H = t_addr >> 8
        t_addr_L = t_addr & 0xFF
        t_ch = int(setting.target_channel)
        payload = bytes([t_addr_H, t_addr_L, t_ch])

        if text is None:
            text = input("Send text> ")

        if setting.ascii_text:
            payload = payload + text.encode("utf-8")
        else:
            payload = payload + bytes(text, "utf-8")
    else:
        if text is None:
            text = input("Send text> ")

        payload = text.encode("utf-8")

        count = int(setting.payload_length)
        if len(payload) > count:
            payload = payload[:count]

    print("payload: {0}".format(payload))

    for data in payload:
        bdata = struct.pack("B", data)
        uart.write(bytes(bdata))

    print("SENT\n")
    return