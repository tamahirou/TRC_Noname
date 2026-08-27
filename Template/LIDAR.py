from machine import I2C, Pin
import time

i2c = I2C(1, sda=Pin(2), scl=Pin(3), freq=100000)  # 100kHzに下げておく
ADDR = 0x10

def read_tf02_i2c():
    try:
        i2c.writeto(ADDR, bytes([0x5A, 0x05, 0x00, 0x01, 0x60]))
        time.sleep_ms(20)
        data = i2c.readfrom(ADDR, 9)
    except OSError as e:
        print("I2C error:", e)
        return None, None

    if data[0] == 0x59 and data[1] == 0x59:
        checksum = sum(data[0:8]) & 0xFF
        if checksum == data[8]:
            dist = data[2] | (data[3] << 8)
            strength = data[4] | (data[5] << 8)
            return dist, strength
    return None, None

while True:
    dist, strength = read_tf02_i2c()
    if dist is not None:
        print("距離: {} cm, 強度: {}".format(dist, strength))
    time.sleep(0.05)