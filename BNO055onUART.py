# Written by Kurt Sewell for Oklahoma State University Capstone Design Fall 2025
# FSAE Current Racing Torsion Rig BNO055 Gyroscope over UART
import serial, busio, board
import time
import adafruit_bno055
from serial import Serial
# uart = busio.UART(board.TX, board.RX, baudrate=9600, timeout=1)
uart = Serial("/dev/ttyAMA0", baudrate=115200, timeout=1) 
"""uart sometimes breaks fully and only works again with a new sensor.
Possibly a fried sensor???"""
bno = adafruit_bno055.BNO055_UART(uart)

def getBNO055Data():
    # print("Gyroscope: {} (degrees/s)".format(bno.gyro))
    roll = bno.euler[0]
    pitch = bno.euler[1]
    yaw = bno.euler[2]
    return pitch

