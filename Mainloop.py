import VL53L1Xcode
import BNO055onUART
import HX711Test

def runSensors():
    tofData = VL53L1Xcode.getAngles()
    bnoDAta = BNO055onUART.getBNO055Data()
    # HX711Test.tareHX711()
    # forceData = HX711Test.getHX711Val()
    print("Angles from VL53L1X sensors: {}".format(tofData))
    print("Gyroscope data from BNO055: {}".format(bnoDAta))

runSensors()