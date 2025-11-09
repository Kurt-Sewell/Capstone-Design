# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
import adafruit_blinka
# This example shows using two TSL2491 light sensors attached to TCA9548A channels 0 and 1.
# Use with other I2C sensors would be similar.
import time

import adafruit_vl53l1x
import board

import adafruit_tca9548a

# Create I2C bus as normal
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

# Create the TCA9548A object and give it the I2C bus
tca = adafruit_tca9548a.TCA9548A(i2c)

def distance(sensor):
    """Get distance reading from a VL53L1X sensor with error handling."""
    try:
        return sensor.distance
    except RuntimeError:
        return None

# For each sensor, create it using the TCA9548A channel instead of the I2C object
vl1 = adafruit_vl53l1x.VL53L1X(tca[0])
vl2 = adafruit_vl53l1x.VL53L1X(tca[1])
vl3 = adafruit_vl53l1x.VL53L1X(tca[2])
vl4 = adafruit_vl53l1x.VL53L1X(tca[3])
vl5 = adafruit_vl53l1x.VL53L1X(tca[4])
vl6 = adafruit_vl53l1x.VL53L1X(tca[5])
vl7 = adafruit_vl53l1x.VL53L1X(tca[6])
vl8 = adafruit_vl53l1x.VL53L1X(tca[7])

# After initial setup, can just use sensors as normal.
while True:
    print("Distance 1: {} cm".format(distance(vl1)), "Distance 2: {} cm".format(distance(vl2)), "Distance 3: {} cm".format(distance(vl3)), "Distance 4: {} cm".format(distance(vl4)), "Distance 5: {} cm".format(distance(vl5)), "Distance 6: {} cm".format(distance(vl6)), "Distance 7: {} cm".format(distance(vl7)), "Distance 8: {} cm".format(distance(vl8)))
    time.sleep(0.1)
