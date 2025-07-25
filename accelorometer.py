import time
import math
import random
import csv
import os
from telegram_bot import send_telegram_message
from led_alert import blink_led
from buzzer_alert import buzz_buzzer

# Fall detection with debug and low threshold
def detect_fall(prev_magnitude, curr_magnitude, threshold=0.1):
    diff = abs(curr_magnitude - prev_magnitude)
    print(f"[DEBUG] Magnitude: {curr_magnitude:.5f}, Prev: {prev_magnitude:.5f}, Diff: {diff:.5f}")
    return diff > threshold

# GPIO and LCD setup
try:
    import RPi.GPIO as GPIO
    import I2C_LCD_driver
except ImportError:
    GPIO = None
    I2C_LCD_driver = None

# Accelerometer import or mock
try:
    import adxl345
except ImportError:
    class MockADXL345:
        class DataRate:
            R_100 = 0
        class Range:
            G_16 = 0
        def __init__(self, i2c_port=1, address=0x53):
            pass
        def load_calib_value(self):
            pass
        def set_data_rate(self, rate):
            pass
        def set_range(self, rng, full_res=True):
            pass
        def measure_start(self):
            pass
        def get_3_axis_adjusted(self):
            return (
                random.uniform(-0.05, 0.2),
                random.uniform(-0.05, 0.2),
                random.uniform(-0.05, 1.0)
            )
    adxl345 = type('adxl345', (), {'ADXL345': MockADXL345, 'DataRate': MockADXL345.DataRate, 'Range': MockADXL345.Range})

# Keypad configuration
MATRIX = [[1, 2, 3], [4, 5, 6], [7, 8, 9], ['*', 0, '#']]
ROW = [6, 20, 19, 13]
COL = [12, 5, 16]

if GPIO:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for i in range(3):
        GPIO.setup(COL[i], GPIO.OUT)
        GPIO.output(COL[i], 1)
    for j in range(4):
        GPIO.setup(ROW[j], GPIO.IN, pull_up_down=GPIO.PUD_UP)

# LCD setup
LCD = I2C_LCD_driver.lcd() if I2C_LCD_driver else None

# CSV setup
csv_filename = 'activity_log.csv'
write_header = not os.path.exists(csv_filename)

# Accelerometer setup
acc = adxl345.ADXL345(i2c_port=1, address=0x53)
acc.load_calib_value()
acc.set_data_rate(adxl345.DataRate.R_100)
acc.set_range(adxl345.Range.G_16, full_res=True)
acc.measure_start()

# Variables
step_count = 0
inactive_seconds = 0
prev_z = None
step_threshold = 0.0015
prev_magnitude = None
fall_alert_sent = False

def get_magnitude(x, y, z):
    return math.sqrt(x**2 + y**2 + z**2)

# Main loop
with open(csv_filename, mode='a', newline='') as csvfile:
    fieldnames = ['timestamp', 'x', 'y', 'z', 'posture', 'step_count', 'inactive_seconds']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    if write_header:
        writer.writeheader()

    while True:
        x, y, z = acc.get_3_axis_adjusted()

        # Step detection
        if prev_z is not None and abs(z - prev_z) > step_threshold:
            step_count += 1
            print(f"Step detected! Total steps: {step_count}")
        prev_z = z

        # Posture detection
        pitch = math.degrees(math.atan2(x, math.sqrt(y*y + z*z)))
        roll = math.degrees(math.atan2(y, math.sqrt(x*x + z*z)))

        if abs(pitch) < 30 and abs(roll) < 30:
            posture = "Standing or Walking"
        elif abs(roll) > 60:
            posture = "Lying Down"
        else:
            posture = "Sitting"

        # Inactivity detection
        magnitude = get_magnitude(x, y, z)
        if magnitude < 0.02:
            inactive_seconds += 1
        else:
            inactive_seconds = 0

        # Fall detection
        fall_cooldown_seconds = 10
        last_fall_time = 0

        # Inside main loop
        current_time = time.time()
        if prev_magnitude is not None:
            diff = abs(magnitude - prev_magnitude)
            if detect_fall(prev_magnitude, magnitude):
                if current_time - last_fall_time > fall_cooldown_seconds:
                    print("⚠️ Fall detected! Sending Telegram alert...")
                    send_telegram_message("⚠️ Fall detected for the elderly! Please check immediately.")
                    if GPIO:
                        buzz_buzzer(5)
                        blink_led(5)
                    last_fall_time = current_time  # start cooldown
                    print(f"[FallCheck] Diff: {diff:.5f}, Time since last: {current_time - last_fall_time:.2f}s")
        prev_magnitude = magnitude


        if inactive_seconds > 60:
            print("⚠️ Inactivity detected for over 60 seconds!")

        # Print current status
        print(f"X:{x:.5f}, Y:{y:.5f}, Z:{z:.5f}, Posture: {posture}")
        print(f"Steps taken so far: {step_count}")

        # Write to CSV
        writer.writerow({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'x': round(x, 5),
            'y': round(y, 5),
            'z': round(z, 5),
            'posture': posture,
            'step_count': step_count,
            'inactive_seconds': inactive_seconds
        })
        csvfile.flush()

        # Keypad check to display step count
        if GPIO and LCD:
            key_pressed = None
            for i in range(3):
                GPIO.output(COL[i], 0)
                for j in range(4):
                    if GPIO.input(ROW[j]) == 0:
                        key_pressed = MATRIX[j][i]
                        while GPIO.input(ROW[j]) == 0:
                            time.sleep(0.1)
                GPIO.output(COL[i], 1)
            if key_pressed == 1:
                LCD.lcd_clear()
                LCD.lcd_display_string("Steps taken:", 1)
                LCD.lcd_display_string(str(step_count), 2)

        time.sleep(0.1)  # Prevent crash from too-fast looping
