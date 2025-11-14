import os, time
os.environ["BLINKA_I2C"] = "13"   # ensure this is set before importing board/busio
import board
import busio
import adafruit_tca9548a
from adafruit_vl53l1x import VL53L1X

i2c = busio.I2C(board.SCL, board.SDA) # uses board.SCL and board.SDA
tca = adafruit_tca9548a.TCA9548A(i2c)
vl1 = VL53L1X(tca[0])
vl2 = VL53L1X(tca[1])
# vl3 = VL53L1X(tca[2])
# vl4 = VL53L1X(tca[3])
# vl5 = VL53L1X(tca[4])
# vl6 = VL53L1X(tca[5])
# vl7 = VL53L1X(tca[6])
# vl8 = VL53L1X(tca[7])

def distance(sensor):
    """Get distance reading from a VL53L1X sensor with error handling."""
    try:
        return sensor.distance
    except RuntimeError:
        return None
    
print("Timing Budget: {}".format(vl1.timing_budget))
vl1.start_ranging()
vl2.start_ranging()
    
while True:
    print("Distance 1: {} cm".format(distance(vl1)))
    print("Distance 2: {} cm".format(distance(vl2)))
    vl1.clear_interrupt
    vl2.clear_interrupt 
    # "Distance 3: {} cm".format(distance(vl3)), "Distance 4: {} cm".format(distance(vl4)), "Distance 5: {} cm".format(distance(vl5)), "Distance 6: {} cm".format(distance(vl6)), "Distance 7: {} cm".format(distance(vl7)), "Distance 8: {} cm".format(distance(vl8)))
    time.sleep(1)