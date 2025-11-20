# Written by Kurt Sewell for Oklahoma State University Capstone Design Fall 2025
# FSAE Current Racing Torsion Rig VL53L1X ToF Sensors
import os, time, math
os.environ["BLINKA_I2C"] = "13"   # ensure this is set before importing board/busio
import board
import busio
import adafruit_tca9548a
from adafruit_vl53l1x import VL53L1X
import numpy as np

i2c = busio.I2C(board.SCL, board.SDA) # uses board.SCL and board.SDA
tca = adafruit_tca9548a.TCA9548A(i2c)
tof = [None] * 8

def test():
    print("Starting test...")
    return

values = np.array([[0, 0, 0, 0, 0, 0, 0, 0],
                   [0, 0, 0, 0, 0, 0, 0, 0],
                   [0, 0, 0, 0, 0, 0, 0, 0],
                   [0, 0, 0, 0, 0, 0, 0, 0],
                   [0, 0, 0, 0, 0, 0, 0, 0],
                   [0, 0, 0, 0, 0, 0, 0, 0],
                   [0, 0, 0, 0, 0, 0, 0, 0],
                   [0, 0, 0, 0, 0, 0, 0, 0]])
ch = 8
adj = np.array([[100, 100, 100, 100, 100, 100, 100, 100],
                [100, 100, 100, 100, 100, 100, 100, 100],
                [100, 100, 100, 100, 100, 100, 100, 100],
                [100, 100, 100, 100, 100, 100, 100, 100],
                [100, 100, 100, 100, 100, 100, 100, 100],
                [100, 100, 100, 100, 100, 100, 100, 100],
                [100, 100, 100, 100, 100, 100, 100, 100],
                [100, 100, 100, 100, 100, 100, 100, 100]])  # adjust array to calibrate initial distance
theta = [0] * ch
for i in range(ch):
    try:
        tof[i] = VL53L1X(tca[i])
        tof[i].start_ranging()
        tof[i].timing_budget = 500
        # print(tof[i], "At position", i)
    except:
        pass
    
#print("Timing Budget: {}".format(tof[0].timing_budget))

    
def getAngles(first=False): # returns list of angles from each ToF sensor
    for j in range(8):
        for i in range(ch):
            try:
                if first == True:   # on first run, calibrate initial distance to zero the sensors
                    adj[i][j] = tof[i].distance # set adj to initial distance
                    values[i][j] = adj[i][j]    # do this to avoid zero division error
                    tof[i].clear_interrupt()
                else:
                    values[i][j] = tof[i].distance  # get distance readings for hypotenuse
                    tof[i].clear_interrupt()
            except:
                pass
        time.sleep(tof[0].timing_budget * .001)
    # print(values)
    for i in range(ch):
        try:
            theta[i] = math.degrees(math.acos(np.mean(adj[i])/(np.mean(values[i]))))    #calculate angle of deflection in degrees
            print(theta[i])
        except:
             # print("Problem with angle calculation", i + 1)
            pass
        # print("Hypotenuse", i+1, ": {}".format(np.mean(values[i])))
        # print("Angle of Def", i+1, ": {} deg".format(theta[i]))
    return theta
