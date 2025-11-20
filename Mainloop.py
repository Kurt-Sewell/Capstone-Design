# Written by Kurt Sewell for Oklahoma State University Capstone Design Fall 2025
# FSAE Current Racing Torsion Rig Main Loop and GUI
import VL53L1Xcode
import BNO055onUART
import dataLogger.py
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

MAX_LOAD = 20000  #pounds
WARNING_LOAD = 1700 #pounds
TOF_CHANNELS = 8
TOF_ZEROS = [0] * TOF_CHANNELS
PITCHZERO = 0
forceData = []
tofs = [[] for i in range(8)]
filename = dataLogger.createUniqueFilename(["Force_lb", "ToF1_deg", "ToF2_deg", "ToF3_deg", "ToF4_deg", "ToF5_deg", "ToF6_deg", "ToF7_deg", "ToF8_deg", "Gyro_Pitch_deg"])

def getZeros(t=False, b=False):
    global TOF_ZEROS
    global PITCHZERO
    if t:
        return TOF_ZEROS
    elif b:
        return PITCHZERO
    else:
        TOF_ZEROS = VL53L1Xcode.getAngles()
        PITCHZERO = BNO055onUART.getBNO055Data()

def runSensors():
    global PITCHZERO, TOF_ZEROS
    forceData.append(int(entry.get()))
    if len(forceData) == 1:
        tofData = VL53L1Xcode.getAngles(True)
        bnoDAta = BNO055onUART.getBNO055Data()
    else:
        tofData = VL53L1Xcode.getAngles(False)
        bnoDAta = BNO055onUART.getBNO055Data()
    # print("Angles from VL53L1X sensors: {}".format(tofData))
    # print("Gyroscope data from BNO055: {}".format(bnoDAta))
    # print("Force data: {}".format(forceData))

    return tofData, bnoDAta, forceData

def updateDashboard():
    tofData, bnoData, forceData = runSensors()
    for list, val in zip(tofs, tofData):
        list.append(val)

    #BNO055 Labels
    bnoLab.config(text=f"Gyroscope Pitch: {bnoData:.2f}"+chr(176), font=("Helvetica", 14))
    #HX711 Labels
    forceLab.config(text=f"Last Force Applied: {forceData[len(forceData)-1]:.2f} lbs", font=("Helvetica", 14))
    for line, sensor in zip(lines, tofs):
        line.set_data(forceData, sensor)
    dataLogger.writeData(filename, tofData, bnoData, forceData)
    ax.relim()
    ax.autoscale_view()
    canvas.draw()

root = tk.Tk()
root.title("FSAE Torsion Rig Dashboard")
root.geometry("600x400")

bnoLab = tk.Label(root, text="Gyroscope Pitch:")
forceLab = tk.Label(root, text="Last Force Applied:")
entry = tk.Entry(root, width=10)
calcButton = tk.Button(root, text="Calculate!", font=("Helvetica", 14), command=updateDashboard)


bnoLab.pack(pady=10)
forceLab.pack(padx=10)
entry.pack(padx=10)
calcButton.pack(pady=10)

f = Figure(figsize=(5,5))
f.suptitle("Angle of Deflection vs Load Applied", fontsize=16)
ax = f.add_subplot(111)
ax.set_xlabel("Force (lb)")
ax.set_ylabel("Angle (deg)")
ax.grid(True)
lines = [ax.plot([], [], label=f"ToF{i+1}", marker='o')[0] for i in range(8)]
ax.legend()

canvas = FigureCanvasTkAgg(f, master=root)
canvas.get_tk_widget().pack(fill="both", expand=True)


root.mainloop()