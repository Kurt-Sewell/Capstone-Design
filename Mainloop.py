import os
os.environ["BLINKA_I2C"] = "13"
import time, busio, digitalio, board
import VL53L1Xcode
#import BNO055onUART
import HX711Test

# from adafruit_vl53l1x import VL53L1X
# import board

# import adafruit_tca9548a
# import adafruit_bno055, serial

# uart = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1)
# bno = adafruit_bno055.BNO055_UART(uart)

# Create I2C bus as normal
# i2c = busio.I2C(board.SCL, board.SDA)  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

# Create the TCA9548A object and give it the I2C bus
# tca = adafruit_tca9548a.TCA9548A(i2c)

tofData = VL53L1Xcode.getAngles()
# bnoDAta = BNO055onUART.getBNO055Data()
# HX711Test.tareHX711()
# forceData = HX711Test.getHX711Val()
print("Angles from VL53L1X sensors: {}".format(tofData))
