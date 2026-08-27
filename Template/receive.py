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
                print("RECEIVED")
                print(payload) 
                print("RSSI: {0} dBm".format(rssi))
                break
            else:
                print("RECEIVED")
                print(payload) 
                break
    print("\n")
    
