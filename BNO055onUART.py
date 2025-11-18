import serial, busio, board
import time
import adafruit_bno055
from serial import Serial
# uart = busio.UART(board.TX, board.RX, baudrate=9600, timeout=1)
uart = Serial("/dev/ttyAMA0", baudrate=115200, timeout=1) 
"""uart sometimes breaks fully and only works again with a new sensor.
Possibly a fried sensor???"""
bno = adafruit_bno055.BNO055_UART(uart)

last_temp = 0xFFFF

def temp():
    global last_temp
    result = bno.temperature
    if abs(result - last_temp) == 128:
        result = bno.temperature
        if abs(result - last_temp) == 128:
            return 0b00111111 & result
    last_temp = result
    return result

def getBNO055Data():
    # print("Temperature: {} degrees C".format(temp()))
    # print("Accelerometer: {} (m/s^2)".format(bno.acceleration))
    print("Gyroscope: {} (degrees/s)".format(bno.gyro))
    # print("Magnetometer: {} (microteslas)".format(bno.magnetic))
    # print("Euler angles: {} (degrees)".format(bno.euler))
    # print("Quaternion: {}".format(bno.quaternion))
    # print("Linear acceleration: {} (m/s^2)".format(bno.linear_acceleration))
    # print("Gravity: {} (m/s^2)".format(bno.gravity))
    return bno.gyro

