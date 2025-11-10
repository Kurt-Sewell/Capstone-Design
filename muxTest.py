import os
os.environ["BLINKA_I2C"] = "13"   # ensure this is set before importing board/busio
import time
import board
import busio
import adafruit_tca9548a
from adafruit_bus_device.i2c_device import I2CDevice

i2c = busio.I2C(board.SCL, board.SDA)
tca = adafruit_tca9548a.TCA9548A(i2c)

def scan_channel(ch):
    bus = tca[ch]
    found = []
    for addr in range(0x03, 0x78):
        try:
            I2CDevice(bus, addr)
            found.append(hex(addr))
        except Exception:
            pass
    return found

for ch in range(8):
    print("Channel", ch, "devices:", scan_channel(ch))