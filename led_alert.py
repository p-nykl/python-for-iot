import RPi.GPIO as GPIO
from time import sleep

LED_PIN = 24

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(LED_PIN, GPIO.OUT)

def blink_led(duration_seconds=5):
    print("🔴 Blinking LED...")
    end_time = time.time() + duration_seconds
    while time.time() < end_time:
        GPIO.output(LED_PIN, 1)  # Turn LED ON
        sleep(1)                 # ON for 1 second
        GPIO.output(LED_PIN, 0)  # Turn LED OFF
        sleep(1)                 # OFF for 1 second
