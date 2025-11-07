# sensors.py
# Reads real sensors only. No random fallback.

import threading, time, math

# --- Fill these with your actual rig measurements on the Pi ---
L_BASELINE_MM = 100.0     # distance pivot→sensor (measure)
ARM_LENGTH_M  = 0.25      # lever arm (measure)
TOF_MODEL     = "VL53L1X"
HX_DT_PIN     = 5
HX_SCK_PIN    = 6
HX_SCALE_LBS  = 2280.0    # set this after calibration
# --------------------------------------------------------------

try:
    import board, busio
    from adafruit_vl53l1x import VL53L1X
    HAVE_TOF = True
except:
    HAVE_TOF = False

try:
    from HX711 import HX711
    HAVE_HX = True
except:
    HAVE_HX = False


class SensorReader:
    def __init__(self, target_hz=20.0):
        self.force_lbs = 0.0
        self.angle_deg = 0.0
        self._stop = threading.Event()
        self._dt = 1.0 / target_hz

        # ToF
        self._tof = None
        if HAVE_TOF:
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                tof = VL53L1X(i2c)
                tof.distance_mode = 1
                tof.timing_budget = 50
                tof.start_ranging()
                self._tof = tof
            except:
                self._tof = None

        # HX711
        self._hx = None
        if HAVE_HX:
            try:
                hx = HX711(dout_pin=HX_DT_PIN, pd_sck_pin=HX_SCK_PIN)
                hx.reset()
                hx.tare()
                if hasattr(hx, "set_scale_ratio"):
                    hx.set_scale_ratio(HX_SCALE_LBS)
                self._hx = hx
            except:
                self._hx = None

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            # ToF → distance → angle
            if self._tof and self._tof.data_ready:
                try:
                    d_mm = float(self._tof.distance) * 10.0  # convert cm → mm
                    self._tof.clear_interrupt()
                    self.angle_deg = math.degrees(math.atan2(max(1e-6, d_mm), L_BASELINE_MM))
                except:
                    pass  # leave last value unchanged

            # HX711 force
            if self._hx:
                try:
                    self.force_lbs = float(self._hx.get_weight_mean(3))
                except:
                    pass  # leave last value unchanged

            time.sleep(self._dt)

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1)
