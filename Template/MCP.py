from machine import I2C, Pin
import time

MCP = 0x20
IODIR, OLAT, BIT = 0x01, 0x15, 5

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100000)
print("1: i2c ok")

i2c.writeto_mem(MCP, IODIR, bytes([i2c.readfrom_mem(MCP, IODIR, 1)[0] & ~(1 << BIT)]))
i2c.writeto_mem(MCP, OLAT,  bytes([i2c.readfrom_mem(MCP, OLAT,  1)[0] |  (1 << BIT)]))
print("2: CE high")

time.sleep(3)
print("3: scan:", [hex(a) for a in i2c.scan()])

for addr in (0x50, 0x54):
    for i in range(5):
        try:
            print(hex(addr), i, i2c.readfrom(addr, 32))
        except OSError as e:
            print(hex(addr), i, "ERR", e)
        time.sleep_ms(200)
print("done")