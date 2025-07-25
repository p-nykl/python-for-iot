import RPi.GPIO as GPIO
from time import sleep

def buzz_buzzer(duration=5):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(18, GPIO.OUT)
    end_time = duration
    while end_time > 0:
        GPIO.output(18, 1)
        sleep(0.5)
        GPIO.output(18, 0)
        sleep(0.5)
        end_time -= 1
