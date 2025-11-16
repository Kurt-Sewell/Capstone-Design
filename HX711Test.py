import time
import board
import digitalio

# On Linux/Blinka the 'microcontroller' module may not implement
# disable_interrupts/enable_interrupts which the CircuitPython
# HX711 driver expects. Provide safe no-op shims so the driver
# can run on Raspberry Pi without disabling interrupts.
try:
    import microcontroller
    if not hasattr(microcontroller, "disable_interrupts"):
        class _NoopDisable:
            def __enter__(self):
                return None
            def __exit__(self, exc_type, exc, tb):
                return False

        def disable_interrupts():
            # Return an object so both styles work:
            #   state = disable_interrupts(); ...; enable_interrupts(state)
            # and
            #   with disable_interrupts(): ...
            return _NoopDisable()

        def enable_interrupts(state=None):
            return None

        microcontroller.disable_interrupts = disable_interrupts
        microcontroller.enable_interrupts = enable_interrupts
except Exception:
    # If microcontroller import fails for any reason, continue; the
    # HX711 library will raise the original error when used.
    pass

from adafruit_hx711.hx711 import HX711
from adafruit_hx711.analog_in import AnalogIn

data = digitalio.DigitalInOut(board.D6)
# data = 31
data.direction = digitalio.Direction.INPUT
clock = digitalio.DigitalInOut(board.D11)
clock.direction = digitalio.Direction.OUTPUT

hx711 = HX711(data, clock)
channel_a = AnalogIn(hx711, HX711.CHAN_A_GAIN_128)
tend = time.monotonic() + 5.0
zeros = []
while time.monotonic() < tend:
    # hx711.tare_value_a(hx711.get_value(hx711.read_channel_raw(HX711.CHAN_A_GAIN_128)))
    try:
        v = channel_a.value
        zeros.append(v)
    except:
        pass
    time.sleep(0.01)
print("Zero readings over 5 seconds: {} samples".format(len(zeros)))
hxZero = sum(zeros) / len(zeros)
print("Calculated zero offset: {}".format(hxZero))

# def getVal():
#     # AnalogIn.value is a property, not a callable function
#     return channel_a.value

while True:
    print("Reading: {}".format(channel_a.value - hxZero))
    time.sleep(1)