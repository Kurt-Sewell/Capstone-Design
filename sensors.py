# sensors.py
# Reads sensor inputs. If hardware isn't there, it just makes random numbers.
# Dashboard pulls the latest values whenever it updates.

import threading, time, random, math

L_BASELINE_MM = 100.0     # distance pivot→sensor (measure later)
ARM_LENGTH_M  = 0.25      # lever arm (measure later)
TOF_MODEL     = "VL53L1X"
HX_DT_PIN     = 5
HX_SCK_PIN    = 6
HX_SCALE_LBS  = 2280.0    # adjust after calibration

try:
    import board, busio
    HAVE_I2C = True
except:
    HAVE_I2C = False

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

        self._tof = None
        self._hx = None

        # ToF sensor
        if HAVE_I2C:
            try:
                import adafruit_vl53l1x
                i2c = busio.I2C(board.SCL, board.SDA)
                tof = adafruit_vl53l1x.VL53L1X(i2c)
                tof.distance_mode = 1
                tof.timing_budget = 50
                tof.start_ranging()
                self._tof = tof
            except:
                pass

        # HX711
        if HAVE_HX:
            try:
                hx = HX711(dout_pin=HX_DT_PIN, pd_sck_pin=HX_SCK_PIN)
                hx.reset()
                hx.tare()
                if hasattr(hx, "set_scale_ratio"):
                    hx.set_scale_ratio(HX_SCALE_LBS)
                self._hx = hx
            except:
                pass

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            # distance → angle
            d = self._read_distance_mm()
            if d is not None:
                self.angle_deg = math.degrees(math.atan2(max(1e-6, d), L_BASELINE_MM))

            # force
            self.force_lbs = self._read_force_lbs()

            time.sleep(self._dt)

    def _read_distance_mm(self):
        if not self._tof:
            return random.uniform(80, 120)
        try:
            if not self._tof.data_ready:
                return None
            # sensor returns cm → mm
            val_mm = float(self._tof.distance) * 10.0
            self._tof.clear_interrupt()
            return val_mm
        except:
            return None

    def _read_force_lbs(self):
        if not self._hx:
            return random.uniform(0, 2000)
        try:
            return float(self._hx.get_weight_mean(3))
        except:
            return random.uniform(0, 2000)

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1)

