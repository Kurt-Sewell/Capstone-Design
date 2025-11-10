# sensors.py
# Pi-only. Safe with NO hardware attached: scans TCA channels and only inits present devices.

import math, time, threading
import board, busio
from adafruit_tca9548a import TCA9548A

# Try optional drivers (BNO055, VL53L1X, HX711); 
try:
    from adafruit_vl53l1x import VL53L1X
    HAVE_VL53 = True
except Exception:
    HAVE_VL53 = False

try:
    from adafruit_bno055 import BNO055_I2C
    HAVE_BNO = True
except Exception:
    HAVE_BNO = False

try:
    from HX711 import HX711
    HAVE_HX = True
except Exception:
    HAVE_HX = False

# ---- rig constants (edit for rig) ----
L_BASELINE_MM = 100.0              # pivot→sensor baseline (mm)
ARM_LENGTH_M  = 0.25               # lever arm (m) used by dashboard torque calc
TCA_CHANNELS  = [0,1,2,3,4,5,6,7]  # TCA9548A channels to try
HX_DT_PIN     = 5                  # BCM DOUT
HX_SCK_PIN    = 6                  # BCM SCK
HX_SCALE_LBS  = 2280.0             # HX711 scale (lbs)
USE_BNO_FOR_ANGLE = True           # selected angle for UI: BNO pitch vs avg(ToF)
BNO_AXIS = "pitch"                 # "pitch" | "roll" | "yaw"
TARGET_HZ = 20.0
# -------------------------------------------

class SensorReader:
    def __init__(self, target_hz: float = TARGET_HZ):
        self.force_lbs = 0.0
        # We size this to number of channels, but only some will be “active”
        self.angles_tof_deg = [0.0] * len(TCA_CHANNELS)   # S1..S8 by channel order
        self.tof_active = [False] * len(TCA_CHANNELS)     # True if a ToF is found on that channel

        self.bno_euler_deg = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
        self.angle_deg = 0.0  # selected angle for UI (BNO or avg ToF)

        self._dt = 1.0 / float(target_hz)
        self._stop = threading.Event()

        # I2C root and multiplexer
        self._i2c = busio.I2C(board.SCL, board.SDA)
        self._tca = TCA9548A(self._i2c)

        # ----- Detect / init ToF per channel (non-blocking if missing) -----
        self._tof = [None] * len(TCA_CHANNELS)
        if HAVE_VL53:
            for i, ch in enumerate(TCA_CHANNELS):
                try:
                    ch_i2c = self._tca[ch]
                    # Quick scan on this channel
                    addrs = ch_i2c.scan()  # returns list of ints
                    if 0x29 in addrs:
                        s = VL53L1X(ch_i2c)
                        s.distance_mode = 1      # short (indoors)
                        s.timing_budget = 50     # ms
                        s.start_ranging()
                        self._tof[i] = s
                        self.tof_active[i] = True
                except Exception:
                    # leave _tof[i] as None
                    pass

        # ----- BNO055 on root I2C (optional) -----
        self._bno = None
        if HAVE_BNO:
            try:
                self._bno = BNO055_I2C(self._i2c)
            except Exception:
                self._bno = None

        # ----- HX711 (optional) -----
        self._hx = None
        if HAVE_HX:
            try:
                hx = HX711(dout_pin=HX_DT_PIN, pd_sck_pin=HX_SCK_PIN)
                hx.reset(); hx.tare()
                if hasattr(hx, "set_scale_ratio"):
                    hx.set_scale_ratio(HX_SCALE_LBS)
                self._hx = hx
            except Exception:
                self._hx = None

        self._th = threading.Thread(target=self._loop, daemon=True)
        self._th.start()

    def _loop(self):
        while not self._stop.is_set():
            # Force (HX711)
            if self._hx:
                try:
                    self.force_lbs = float(self._hx.get_weight_mean(3))
                except Exception:
                    pass

            # VL53L1X on each detected channel
            for i, s in enumerate(self._tof):
                if not s:
                    continue
                try:
                    if s.data_ready:
                        # NOTE: Adafruit VL53L1X .distance is in cm → convert to mm
                        d_mm = float(s.distance) * 10.0
                        s.clear_interrupt()
                        self.angles_tof_deg[i] = math.degrees(
                            math.atan2(max(1e-6, d_mm), L_BASELINE_MM)
                        )
                except Exception:
                    pass  # keep last

            # BNO055 Euler (optional)
            if self._bno:
                try:
                    e = self._bno.euler  # (roll, pitch, yaw) in degrees
                    if e and all(v is not None for v in e):
                        self.bno_euler_deg["roll"]  = float(e[0])
                        self.bno_euler_deg["pitch"] = float(e[1])
                        self.bno_euler_deg["yaw"]   = float(e[2])
                except Exception:
                    pass

            # Selected angle for UI
            self.angle_deg = self._select_angle()
            time.sleep(self._dt)

    def _select_angle(self) -> float:
        # Prefer BNO if configured and present
        if USE_BNO_FOR_ANGLE and self._bno:
            return float(self.bno_euler_deg.get(BNO_AXIS, 0.0))
        # Otherwise average only the channels that actually have a ToF
        vals = [ang for ang, active in zip(self.angles_tof_deg, self.tof_active) if active]
        return sum(vals) / len(vals) if vals else 0.0

    def stop(self):
        self._stop.set()
        self._th.join(timeout=1.0)



