# sensors.py
# Pi-only. Adafruit HX711 (D6=DOUT, D11=SCK) -> raw counts & pounds.
# Optional: TCA9548A->VL53L1X, BNO055 (UART). Non-blocking, prints brief HX debug.

import math, time, threading, os
os.environ["BLINKA_I2C"] = "13"
import board, busio, digitalio, serial
from adafruit_tca9548a import TCA9548A
import numpy as np

# Optional drivers (load if installed)
try:
    from adafruit_vl53l1x import VL53L1X
    HAVE_VL53 = True
except Exception:
    HAVE_VL53 = False

try:
    import adafruit_bno055
    HAVE_BNO = True
except Exception:
    HAVE_BNO = False

# Adafruit CircuitPython HX711
from adafruit_hx711.hx711 import HX711
from adafruit_hx711.analog_in import AnalogIn

# -------- Rig constants --------
L_BASELINE_MM = 100.0
ARM_LENGTH_M  = 0.25
TCA_CHANNELS  =  8 #[0,1,2,3,4,5,6,7]

# HX711 pins: D6 = DOUT (input), D11 = SCK (output)
HX_DATA_PIN = digitalio.DigitalInOut(board.D6)   # BCM6, phys 31
HX_CLK_PIN  = digitalio.DigitalInOut(board.D11)  # BCM11, phys 23
HX_DATA_PIN.direction = digitalio.Direction.INPUT
HX_CLK_PIN.direction  = digitalio.Direction.OUTPUT

# Calibration: set after two-point calibration
HX_COUNTS_PER_LB = 10000.0      # <-- placeholder: adjust after you see raw moving
HX_STARTUP_TARE_S = 1.0         # seconds to average zero at startup
HX_SMOOTH_N = 5                 # moving average window for force

USE_BNO_FOR_ANGLE = True
BNO_AXIS = "pitch"
TARGET_HZ = 20.0
# --------------------------------


class SensorReader:
    def __init__(self, target_hz: float = TARGET_HZ):
        # outputs the dashboard reads
        self.force_lbs = 0.0
        self.force_raw = 0            # <- raw counts exposed for debugging
        self.angles_tof_deg = [0.0] * TCA_CHANNELS
        self.tof_active = [False] * TCA_CHANNELS
        self.bno_euler_deg = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
        self.angle_deg = 0.0

        self._dt = 1.0 / float(target_hz)
        self._stop = threading.Event()

        # I2C + TCA
        self._i2c = busio.I2C(board.SCL, board.SDA)
        self._tca = TCA9548A(self._i2c)

        # VL53L1X per channel (only init if present)
        self._tof = [None] * TCA_CHANNELS
        if HAVE_VL53:
            # if 0x29 in self._tca[i].scan():
            for i in range(TCA_CHANNELS):
                try:
                    self._tof[i] = VL53L1X(self._tca[i])
                    self._tof[i].start_ranging()
                    self._tof[i].timing_budget = 500
                    self.tof_active[i] = True
                    print(self._tof[i], "At position", i)
                except:
                    pass
        #     for i, ch in enumerate(TCA_CHANNELS):
        #         try:
        #             ch_i2c = self._tca[ch]
        #             if 0x29 in ch_i2c.scan():
        #                 s = VL53L1X(ch_i2c)
        #                 s.distance_mode = 1    # short
        #                 # s.timing_budget = 50   # ms
        #                 s.start_ranging()
        #                 self._tof[i] = s
        #                 self.tof_active[i] = True
        #         except Exception:
        #             pass

        # BNO055 (UART preferred)
        self._bno = None
        if HAVE_BNO:
            try:
                ser = serial.Serial('/dev/ttyAMA0', baudrate=115200, timeout=1)
                self._bno = adafruit_bno055.BNO055_UART(ser)
            except Exception:
                self._bno = None

        # HX711: bring up quickly
        self._hx = HX711(HX_DATA_PIN, HX_CLK_PIN)
        self._hx_chan = AnalogIn(self._hx, HX711.CHAN_A_GAIN_128)

        # Startup tare (average zero)
        t_end = time.monotonic() + HX_STARTUP_TARE_S
        zeros = []
        while time.monotonic() < t_end:
            try:
                v = self._hx_chan.value
                zeros.append(v)
            except Exception:
                pass
            time.sleep(0.01)
        self._hx_zero = int(sum(zeros) / max(1, len(zeros)))

        self._force_buf = []

        # short boot-time debug: show raw every 0.5s for 5 seconds
        self._dbg_until = time.monotonic() + 5.0
        self._dbg_next  = 0.0

        # start background read loop
        self._th = threading.Thread(target=self._loop, daemon=True)
        self._th.start()

    def _loop(self):
        while not self._stop.is_set():
            # -------- HX711: raw -> lbs --------
            try:
                raw = int(self._hx_chan.value)
                self.force_raw = raw
                lbs = (raw - self._hx_zero) / float(HX_COUNTS_PER_LB)

                self._force_buf.append(lbs)
                if len(self._force_buf) > HX_SMOOTH_N:
                    self._force_buf.pop(0)
                self.force_lbs = sum(self._force_buf) / len(self._force_buf)

                # boot-time console debug
                now = time.monotonic()
                if now < self._dbg_until and now >= self._dbg_next:
                    self._dbg_next = now + 0.5
                    print(f"[HX711] raw={raw} zero={self._hx_zero} lbs≈{self.force_lbs:.2f}")
            except Exception:
                # keep last values on transient error
                pass

            # -------- VL53L1X angles (if present) --------
            for i in range(TCA_CHANNELS):
                try:
                    d_mm = self._tof[i].distance * 10.0  # cm -> mm
                    self._tof[i].clear_interrupt()
                    self.angles_tof_deg[i] = math.degrees(
                        math.atan2(max(1e-6, d_mm), L_BASELINE_MM)
                    )
                    print(self.angles_tof_deg[i])
                except:
                    print("Problem with ToF sensor", i+1)
                    pass
            # for i, s in enumerate(self._tof):
            #     if not s:
            #         continue
            #     try:
            #         if s.data_ready:
            #             d_mm = float(s.distance) * 10.0  # cm -> mm
            #             s.clear_interrupt()
            #             self.angles_tof_deg[i] = math.degrees(
            #                 math.atan2(max(1e-6, d_mm), L_BASELINE_MM)
            #             )
            #             print(self.angles_tof_deg[i])
            #     except Exception:
            #         pass
            #         print("Problem with ToF sensor", s, i)

            # -------- BNO055 Euler (if present) --------
            if self._bno:
                try:
                    e = self._bno.euler
                    if e and all(v is not None for v in e):
                        self.bno_euler_deg["roll"]  = float(e[0])
                        self.bno_euler_deg["pitch"] = float(e[1])
                        self.bno_euler_deg["yaw"]   = float(e[2])
                except Exception:
                    pass

            # -------- Selected angle for UI --------
            self.angle_deg = self._select_angle()

            time.sleep(self._dt)

    def _select_angle(self) -> float:
        if USE_BNO_FOR_ANGLE and self._bno:
            return float(self.bno_euler_deg.get(BNO_AXIS, 0.0))
        vals = [ang for ang, active in zip(self.angles_tof_deg, self.tof_active) if active]
        return sum(vals) / len(vals) if vals else 0.0

    def stop(self):
        self._stop.set()
        self._th.join(timeout=1.0)



