# sensors.py
import threading, time, random, math

# -----------------------------------------------------------
# PLACEHOLDERS TO FILL IN *ONCE YOU ARE BACK AT THE PI*
# -----------------------------------------------------------
# ToF baseline distance (mm) → distance between pivot and sensor
L_BASELINE_MM = 100.0   # TODO: measure and update

# ToF MODEL (pick one later):
#   "VL53L4CD"
#   "VL53L1X"
#   "VL53L0X"
TOF_MODEL = "VL53L4CD"   # TODO: confirm your exact sensor model

# HX711 GPIO pins (BCM numbering, NOT physical pin numbers)
HX_DT_PIN = 5            # TODO: change to your actual pin
HX_SCK_PIN = 6           # TODO: change to your actual pin

# Lever arm (distance from force application point to pivot)
ARM_LENGTH_M = 0.25      # TODO: measure and update
# -----------------------------------------------------------


# Attempt imports (fail silently → fallback mode)
try:
    import board, busio
    HAVE_I2C = True
except Exception:
    HAVE_I2C = False

try:
    from HX711 import HX711
    HAVE_HX = True
except Exception:
    HAVE_HX = False


class SensorReader:
    """
    Reads:
      - ToF distance → angle (deg)
      - HX711 load cell → force (lbs)
    If hardware is missing (e.g., running on laptop):
      → returns random values
    """
    def __init__(self, target_hz=20.0):
        self.force_lbs = 0.0
        self.angle_deg = 0.0
        self._stop = threading.Event()
        self.period = 1.0 / float(target_hz)

        self._tof = None
        self._hx = None

        # Try to initialize ToF
        if HAVE_I2C:
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                if TOF_MODEL == "VL53L4CD":
                    import adafruit_vl53l4cd
                    tof = adafruit_vl53l4cd.VL53L4CD(i2c)
                    tof.inter_measurement = 0
                    tof.timing_budget = 50
                    tof.start_ranging()
                    self._tof = tof
            except:
                self._tof = None

        # Try to initialize HX711
        if HAVE_HX:
            try:
                hx = HX711(dout_pin=HX_DT_PIN, pd_sck_pin=HX_SCK_PIN)
                hx.reset()
                hx.tare()  # Zero out scale
                # TODO: calibrate later → replace 2280.0 after calibration
                hx.set_scale_ratio(2280.0)
                self._hx = hx
            except:
                self._hx = None

        # Start background update thread
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            try:
                # ToF reading
                if self._tof:
                    if self._tof.data_ready:
                        d_mm = float(self._tof.distance)
                        self._tof.clear_interrupt()
                    else:
                        d_mm = None
                else:
                    d_mm = random.uniform(80.0, 120.0)

                # Convert distance → angle
                if d_mm is None:
                    self.angle_deg = random.uniform(0, 10)
                else:
                    self.angle_deg = math.degrees(math.atan2(max(1e-6, d_mm), L_BASELINE_MM))

                # Force reading
                if self._hx:
                    force_lbs = float(self._hx.get_weight_mean(3))
                else:
                    force_lbs = random.uniform(0.0, 2000.0)

                self.force_lbs = force_lbs

            except:
                # fallback mode
                self.force_lbs = random.uniform(0.0, 2000.0)
                self.angle_deg = random.uniform(0, 10)

            time.sleep(self.period)

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1)
