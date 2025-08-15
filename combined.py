import keypad
import I2C_LCD_driver
from threading import Thread
import queue
import time
import requests 
import dht11
import datetime
from time import sleep
import RPi.GPIO as GPIO
import csv
import os
import math
import random

# Shared components
shared_keypad_queue = queue.Queue()
lcd = None

# Ultrasonic sensor pins
TRIG_PIN = 23
ECHO_PIN = 24

# Daily tracking variables
daily_data = {
    'steps_start': 0,
    'eaten_count': 0,
    'walked_count': 0,
    'feeling_ratings': [],
    'checkins_completed': 0,
    'checkins_missed': 0,
    'last_reset_date': datetime.date.today()
}

# Accelerometer mock class (use real adxl345 if available)
try:
    import adxl345
except ImportError:
    class MockADXL345:
        class DataRate:
            R_100 = 0
        class Range:
            G_16 = 0
        def init(self, i2c_port=1, address=0x53):
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

def key_pressed(key):
    shared_keypad_queue.put(key)

GPIO.setmode(GPIO.BCM)

# Setup ultrasonic sensor pins
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

def get_distance():
    """Get distance from ultrasonic sensor in cm with debug output"""
    try:
        # Send trigger pulse
        GPIO.output(TRIG_PIN, GPIO.HIGH)
        time.sleep(0.00001)  # 10 microseconds
        GPIO.output(TRIG_PIN, GPIO.LOW)
        
        # Initialize variables to avoid reference errors
        pulse_start = 0
        pulse_end = 0
        
        # Measure echo time with timeout
        timeout = time.time() + 1  # 1 second timeout
        
        # Wait for echo start
        while GPIO.input(ECHO_PIN) == GPIO.LOW:
            pulse_start = time.time()
            if pulse_start > timeout:
                print("ULTRASONIC DEBUG: Timeout waiting for echo start")
                return None
        
        # Wait for echo end
        while GPIO.input(ECHO_PIN) == GPIO.HIGH:
            pulse_end = time.time()
            if pulse_end > timeout:
                print("ULTRASONIC DEBUG: Timeout waiting for echo end")
                return None
        
        # Validate that we have valid pulse times
        if pulse_end <= pulse_start:
            print("ULTRASONIC DEBUG: Invalid pulse timing")
            return None
        
        # Calculate distance
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150  # Speed of sound = 34300 cm/s, divide by 2
        distance = round(distance, 2)
        
        # Debug output
        print(f"ULTRASONIC DEBUG: Pulse duration: {pulse_duration:.6f}s, Distance: {distance}cm")
        
        # Return distance if within reasonable range
        if 2 <= distance <= 400:  # Minimum 2cm, maximum 400cm
            return distance
        else:
            print(f"ULTRASONIC DEBUG: Distance {distance}cm out of valid range (2-400cm)")
            return None
            
    except Exception as e:
        print(f"ULTRASONIC DEBUG: Error reading sensor: {e}")
        return None

def reset_daily_data_if_new_day():
    """Reset daily tracking data if it's a new day"""
    global daily_data
    current_date = datetime.date.today()
    
    if current_date != daily_data['last_reset_date']:
        print(f"New day detected! Resetting daily data from {daily_data['last_reset_date']} to {current_date}")
        
        # Save previous day's summary to file before reset
        save_daily_summary_to_file()
        
        # Reset counters but preserve step baseline
        daily_data = {
            'steps_start': 0,  # Will be updated when accelerometer starts
            'eaten_count': 0,
            'walked_count': 0,
            'feeling_ratings': [],
            'checkins_completed': 0,
            'checkins_missed': 0,
            'last_reset_date': current_date
        }

def save_daily_summary_to_file():
    """Save daily summary to CSV file"""
    filename = "daily_summaries.csv"
    file_exists = os.path.isfile(filename)
    
    avg_feeling = sum(daily_data['feeling_ratings']) / len(daily_data['feeling_ratings']) if daily_data['feeling_ratings'] else 0
    
    with open(filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        
        if not file_exists:
            writer.writerow(['Date', 'Steps_Taken', 'Eaten_Count', 'Walked_Count', 'Avg_Feeling', 
                           'Checkins_Completed', 'Checkins_Missed'])
        
        writer.writerow([
            daily_data['last_reset_date'],
            0,  # Steps will be calculated properly in the actual implementation
            daily_data['eaten_count'],
            daily_data['walked_count'],
            round(avg_feeling, 1),
            daily_data['checkins_completed'],
            daily_data['checkins_missed']
        ])

def display_daily_summary():
    """Display comprehensive daily summary"""
    global lcd, daily_data
    
    reset_daily_data_if_new_day()
    
    # Calculate average feeling
    avg_feeling = sum(daily_data['feeling_ratings']) / len(daily_data['feeling_ratings']) if daily_data['feeling_ratings'] else 0
    
    # Determine if user has eaten or walked today
    has_eaten_today = "Yes" if daily_data['eaten_count'] > 0 else "No"
    has_walked_today = "Yes" if daily_data['walked_count'] > 0 else "No"
    
    # Display summary across multiple screens
    screens = [
        # Screen 1: Date and Steps
        [f"Summary {datetime.date.today().strftime('%m/%d')}", f"Steps today: {daily_data.get('steps_today', 0)}"],
        
        # Screen 2: Activities
        [f"Eaten: {has_eaten_today} ({daily_data['eaten_count']}x)", f"Walked: {has_walked_today} ({daily_data['walked_count']}x)"],
        
        # Screen 3: Feelings and Check-ins
        [f"Avg Feeling: {avg_feeling:.1f}/9", f"Check-ins: {daily_data['checkins_completed']}/{daily_data['checkins_completed'] + daily_data['checkins_missed']}"],
        
        # Screen 4: Overall Status
        ["Overall Status:", "Good" if avg_feeling > 6 and daily_data['checkins_completed'] > daily_data['checkins_missed'] else "Check needed"]
    ]
    
    print("\n=== DAILY SUMMARY ===")
    print(f"Date: {datetime.date.today()}")
    print(f"Steps taken today: {daily_data.get('steps_today', 0)}")
    print(f"Times eaten: {daily_data['eaten_count']}")
    print(f"Times walked: {daily_data['walked_count']}")
    print(f"Average feeling: {avg_feeling:.1f}/9")
    print(f"Check-ins completed: {daily_data['checkins_completed']}")
    print(f"Check-ins missed: {daily_data['checkins_missed']}")
    print(f"Has eaten today: {has_eaten_today}")
    print(f"Has walked today: {has_walked_today}")
    print("====================\n")
    
    # Display on LCD
    for i, screen in enumerate(screens):
        lcd.lcd_clear()
        time.sleep(0.1)
        lcd.lcd_display_string(screen[0], 1)
        time.sleep(0.1)
        lcd.lcd_display_string(screen[1], 2)
        
        if i < len(screens) - 1:  # Don't wait after last screen
            time.sleep(3)  # Show each screen for 3 seconds
    
    time.sleep(2)  # Show final screen for 2 seconds

def is_sleep_time():
    """Check if current time is within sleep hours (10 PM to 6 AM)"""
    current_hour = datetime.datetime.now().hour
    return current_hour >= 22 or current_hour < 6

def upload_to_thingspeak(temperature, humidity, steps, x, y, z, magnitude, user_feeling, distance=None):
    API_KEY = 'AVURSRXZ07INDOZO'  # Replace with your actual ThingSpeak Write API Key
    url = "https://api.thingspeak.com/update"
    params = {
        'api_key': API_KEY,
        'field1': temperature,
        'field2': humidity,
        'field3': steps,
        'field4': x,
        'field5': y,
        'field6': z,
        'field7': magnitude,
        'field8': user_feeling
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        print(f"ThingSpeak response status: {response.status_code}")
        print(f"ThingSpeak response text: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Exception during ThingSpeak upload: {e}")
        return False

def send_telegram_message(message):
    TELEGRAM_BOT_TOKEN = '7885273126:AAEpr5Dy9bUXYE3kf9lEH1ww2bXsByE9y5c'
    TELEGRAM_CHAT_ID = '6101168212'
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data, timeout=5)
        print("Telegram message sent successfully")
        return True
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False

def get_magnitude(x, y, z):
    return math.sqrt(x*x + y*y + z*z)  # Fixed the syntax error

def detect_fall(prev_magnitude, curr_magnitude, threshold=0.1):
    if prev_magnitude is None:
        return False
    diff = abs(curr_magnitude - prev_magnitude)
    time.sleep(5)  # Simulate processing delay
    print(f"Magnitude: {curr_magnitude:.5f}, Prev: {prev_magnitude:.5f}, Diff: {diff:.5f}")
    return diff > threshold

def ultrasonic_monitoring_thread(shared_data):
    """Thread for ultrasonic sensor monitoring with enhanced debug output"""
    print("Ultrasonic sensor monitoring started...")
    print("ULTRASONIC DEBUG: Sensor initialized on pins TRIG={}, ECHO={}".format(TRIG_PIN, ECHO_PIN))
    
    # Variables for proximity detection
    person_present_threshold = 200  # cm - person considered present if closer than 2m
    person_absent_threshold = 300   # cm - person considered absent if farther than 3m
    person_present = False
    last_presence_change = time.time()
    absence_alert_sent = False
    prolonged_absence_threshold = 1800  # 30 minutes
    
    # Debug counter for periodic status
    debug_counter = 0
    
    while shared_data['running']:
        try:
            distance = get_distance()
            debug_counter += 1
            
            if distance is not None:
                current_time = time.time()
                
                # Enhanced debug output every 10 readings
                if debug_counter % 10 == 0:
                    print(f"ULTRASONIC STATUS: Distance={distance}cm, Present={person_present}, "
                          f"Threshold_Present={person_present_threshold}cm, Threshold_Absent={person_absent_threshold}cm")
                
                # Determine presence status
                if distance < person_present_threshold:
                    if not person_present:
                        person_present = True
                        last_presence_change = current_time
                        absence_alert_sent = False
                        print(f"ULTRASONIC: Person detected at {distance}cm")
                        
                elif distance > person_absent_threshold:
                    if person_present:
                        person_present = False
                        last_presence_change = current_time
                        print(f"ULTRASONIC: Person left area, distance: {distance}cm")
                
                # Check for prolonged absence (only during wake hours)
                if not person_present and not is_sleep_time():
                    absence_duration = current_time - last_presence_change
                    
                    if absence_duration > prolonged_absence_threshold and not absence_alert_sent:
                        absence_minutes = int(absence_duration / 60)
                        alert_msg = f"⚠ PROLONGED ABSENCE ALERT: No person detected for {absence_minutes} minutes. Please check on the elderly person."
                        print(alert_msg)
                        send_telegram_message(alert_msg)
                        absence_alert_sent = True
                
                # Update shared data
                shared_data.update({
                    'distance': distance,
                    'person_present': person_present,
                    'absence_duration': current_time - last_presence_change if not person_present else 0
                })
                
            else:
                shared_data['distance'] = None
                if debug_counter % 5 == 0:  # Show error every 5 attempts
                    print("ULTRASONIC DEBUG: Failed to get distance reading")
                
        except Exception as e:
            print(f"ULTRASONIC DEBUG: Error in monitoring: {e}")
        
        time.sleep(1)  # Check every second

def scheduled_checkin_thread(shared_data):
    """Thread for scheduled check-ins every 4 hours during wake hours"""
    print("Scheduled check-in monitoring started...")
    
    checkin_interval = 4 * 3600  # 4 hours in seconds
    checkin_timeout = 300  # 5 minutes to respond to check-in
    last_checkin_time = time.time()
    waiting_for_checkin = False
    checkin_start_time = 0
    
    while shared_data['running']:
        try:
            current_time = time.time()
            
            # Check if it's time for a scheduled check-in (only during wake hours)
            if not is_sleep_time() and not waiting_for_checkin:
                time_since_last_checkin = current_time - last_checkin_time
                
                if time_since_last_checkin >= checkin_interval:
                    # Trigger check-in
                    waiting_for_checkin = True
                    checkin_start_time = current_time
                    
                    # Display check-in prompt on LCD
                    lcd.lcd_clear()
                    time.sleep(0.1)
                    lcd.lcd_display_string("CHECK-IN TIME!", 1)
                    time.sleep(0.1)
                    lcd.lcd_display_string("Press 1 or 2", 2)
                    
                    # Send telegram notification
                    checkin_msg = "🔔 SCHEDULED CHECK-IN: Please confirm you are okay by pressing 1 (eaten) or 2 (walked) on the device."
                    send_telegram_message(checkin_msg)
                    
                    print("Scheduled check-in triggered - waiting for user response...")
            
            # Check if waiting for check-in response
            if waiting_for_checkin:
                time_waiting = current_time - checkin_start_time
                
                # Check if user has responded (look for any recent activity)
                if shared_data.get('last_user_interaction', 0) > checkin_start_time:
                    # User has responded
                    waiting_for_checkin = False
                    last_checkin_time = current_time
                    daily_data['checkins_completed'] += 1
                    print("Check-in completed by user interaction")
                    
                    # Clear check-in display
                    show_temp_humidity_display(shared_data.get('dht_instance'))
                    
                elif time_waiting > checkin_timeout:
                    # Check-in timeout - send alert
                    waiting_for_checkin = False
                    last_checkin_time = current_time  # Reset to avoid immediate re-trigger
                    daily_data['checkins_missed'] += 1
                    
                    alert_msg = f"🚨 MISSED CHECK-IN ALERT: No response to scheduled check-in for {int(checkin_timeout/60)} minutes. Please check on the elderly person immediately!"
                    print(alert_msg)
                    send_telegram_message(alert_msg)
                    
                    # Clear check-in display
                    show_temp_humidity_display(shared_data.get('dht_instance'))
                    
                    print("Check-in timeout - alert sent")
            
            # Update shared data
            shared_data.update({
                'waiting_for_checkin': waiting_for_checkin,
                'next_checkin_in': checkin_interval - (current_time - last_checkin_time) if not waiting_for_checkin else 0
            })
            
        except Exception as e:
            print(f"Error in scheduled check-in: {e}")
        
        time.sleep(10)  # Check every 10 seconds

# Add these global variables after your existing global variables
buzzer_alert = None
led_alert = None

# Modify the detect_fall function
def detect_fall(prev_magnitude, curr_magnitude, threshold=0.1):
    if prev_magnitude is None:
        return False
    diff = abs(curr_magnitude - prev_magnitude)
    print(f"Magnitude: {curr_magnitude:.5f}, Prev: {prev_magnitude:.5f}, Diff: {diff:.5f}")
    
    # Enhanced fall detection logic
    if diff > threshold:
        print("⚠  POTENTIAL FALL DETECTED!")
        print(f"Magnitude difference: {diff:.5f} (threshold: {threshold})")
        return True
    return False

# Enhanced fall detection and alert function
def handle_fall_detection(x, y, z, magnitude):
    """Enhanced fall detection with multiple criteria"""
    global buzzer_alert, led_alert
    
    # Multiple fall detection criteria
    fall_detected = False
    fall_reason = ""
    
    # Criterion 1: High impact detection (sudden change in acceleration)
    if hasattr(handle_fall_detection, 'prev_magnitude'):
        magnitude_diff = abs(magnitude - handle_fall_detection.prev_magnitude)
        if magnitude_diff > 0.15:  # Adjusted threshold
            fall_detected = True
            fall_reason = f"High impact detected (diff: {magnitude_diff:.3f})"
    
    # Criterion 2: Orientation check (if person is lying down suddenly)
    pitch = math.degrees(math.atan2(x, math.sqrt(y*y + z*z)))
    roll = math.degrees(math.atan2(y, math.sqrt(x*x + z*z)))
    
    if abs(pitch) > 70 or abs(roll) > 70:
        # Check if this is a sudden change to lying position
        if hasattr(handle_fall_detection, 'prev_pitch') and hasattr(handle_fall_detection, 'prev_roll'):
            pitch_change = abs(pitch - handle_fall_detection.prev_pitch)
            roll_change = abs(roll - handle_fall_detection.prev_roll)
            
            if pitch_change > 45 or roll_change > 45:
                fall_detected = True
                fall_reason = f"Sudden orientation change - Pitch: {pitch:.1f}°, Roll: {roll:.1f}°"
    
    # Criterion 3: Low magnitude (free fall detection)
    if magnitude < 0.5:  # Very low acceleration might indicate free fall
        fall_detected = True
        fall_reason = f"Free fall detected (magnitude: {magnitude:.3f})"
    
    # Store previous values for next comparison
    handle_fall_detection.prev_magnitude = magnitude
    handle_fall_detection.prev_pitch = pitch
    handle_fall_detection.prev_roll = roll
    
    return fall_detected, fall_reason

def activate_fall_emergency_alerts():
    """Activate all emergency alerts for fall detection"""
    global buzzer_alert, led_alert, lcd
    
    print("🚨 ACTIVATING FALL EMERGENCY ALERTS 🚨")
    
    # Activate buzzer with urgent pattern
    if buzzer_alert:
        buzzer_alert.start_alert(duration=60, pattern="urgent")  # 1 minute urgent buzzing
    
    # Activate LED with fall alert pattern
    if led_alert:
        led_alert.start_fall_alert(duration=60)  # 1 minute red flashing
    
    # Display emergency message on LCD
    lcd.lcd_clear()
    time.sleep(0.1)
    lcd.lcd_display_string("🚨 FALL DETECTED! 🚨", 1)
    time.sleep(0.1)
    lcd.lcd_display_string("Emergency Alert!", 2)

def stop_fall_alerts():
    """Stop all fall-related alerts"""
    global buzzer_alert, led_alert
    
    if buzzer_alert:
        buzzer_alert.stop_alert()
    
    if led_alert:
        led_alert.stop_alert()
    
    print("Fall alerts stopped")

# Modified accelerometer_monitoring_thread function
def accelerometer_monitoring_thread(shared_data):
    """Thread for continuous accelerometer monitoring with enhanced fall detection"""
    global buzzer_alert, led_alert
    
    # Accelerometer setup
    acc = adxl345.ADXL345(i2c_port=1, address=0x53)
    acc.load_calib_value()
    acc.set_data_rate(adxl345.DataRate.R_100)
    acc.set_range(adxl345.Range.G_16, full_res=True)
    acc.measure_start()
    
    # Variables for accelerometer
    step_count = 0
    inactive_seconds = 0
    prev_z = None
    step_threshold = 0.0015
    prev_magnitude = None
    last_fall_time = 0
    fall_cooldown_seconds = 30  # Increased cooldown to prevent false alarms
    fall_confirmation_time = 5   # Time to confirm fall before triggering alerts
    potential_fall_start = 0
    
    # Set initial step count for daily tracking
    daily_data['steps_start'] = step_count
    
    print("Accelerometer monitoring started with enhanced fall detection...")
    
    while shared_data['running']:
        try:
            x, y, z = acc.get_3_axis_adjusted()
            
            # Step detection
            if prev_z is not None and abs(z - prev_z) > step_threshold:
                step_count += 1
                print(f"Step detected! Total steps: {step_count}")
            prev_z = z
            
            # Update daily steps
            daily_data['steps_today'] = step_count - daily_data['steps_start']
            
            # Posture detection
            pitch = math.degrees(math.atan2(x, math.sqrt(y*y + z*z)))
            roll = math.degrees(math.atan2(y, math.sqrt(x*x + z*z)))
            
            if abs(pitch) < 30 and abs(roll) < 30:
                posture = "Standing or Walking"
            elif abs(roll) > 60:
                posture = "Lying Down"
            else:
                posture = "Sitting"
            
            # Enhanced fall detection
            magnitude = get_magnitude(x, y, z)
            current_time = time.time()
            
            # Check for fall using enhanced detection
            fall_detected, fall_reason = handle_fall_detection(x, y, z, magnitude)
            
            if fall_detected and current_time - last_fall_time > fall_cooldown_seconds:
                if potential_fall_start == 0:
                    potential_fall_start = current_time
                    print(f"⚠  POTENTIAL FALL DETECTED: {fall_reason}")
                    
                    # Start warning alerts (not full emergency yet)
                    if led_alert:
                        led_alert.start_warning_alert(duration=fall_confirmation_time)
                
                # Check if fall is confirmed (sustained for confirmation time)
                elif current_time - potential_fall_start >= fall_confirmation_time:
                    # CONFIRMED FALL - ACTIVATE ALL ALERTS
                    fall_message = f"🚨 FALL CONFIRMED! {fall_reason}. Immediate assistance required!"
                    print(fall_message)
                    
                    # Send Telegram alert
                    detailed_message = (
                        f"🚨 EMERGENCY FALL ALERT 🚨\n"
                        f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Reason: {fall_reason}\n"
                        f"Position: Pitch={pitch:.1f}°, Roll={roll:.1f}°\n"
                        f"Acceleration: {magnitude:.3f}g\n"
                        f"IMMEDIATE ASSISTANCE REQUIRED!"
                    )
                    send_telegram_message(detailed_message)
                    
                    # Activate all emergency alerts
                    activate_fall_emergency_alerts()
                    
                    last_fall_time = current_time
                    potential_fall_start = 0
                    
                    # Log fall to CSV immediately
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    write_fall_data_to_csv(timestamp, x, y, z, magnitude, pitch, roll, fall_reason)
                    
            else:
                # Reset potential fall if conditions are normal
                if potential_fall_start != 0:
                    potential_fall_start = 0
                    if led_alert:
                        led_alert.stop_alert()  # Stop warning alerts
            
            # Inactivity detection (only during wake hours)
            if not is_sleep_time():
                if magnitude < 0.02:
                    inactive_seconds += 1
                    
                    # Visual indicator for inactivity
                    if inactive_seconds == 180 and led_alert:  # 3 minutes
                        led_alert.start_inactive_warning(duration=60)
                        
                else:
                    inactive_seconds = 0
                    # Show normal status if no alerts active
                    if led_alert and not led_alert.is_alerting:
                        led_alert.start_normal_status()
            else:
                inactive_seconds = 0  # Reset during sleep hours
                
            # Inactivity alert (only during wake hours)
            if inactive_seconds > 300:  # 5 minutes of inactivity
                inactivity_message = f"⚠ No movement detected for {inactive_seconds} seconds. Please check on the elderly person."
                print(inactivity_message)
                send_telegram_message(inactivity_message)
                inactive_seconds = 0  # Reset to avoid spam
            
            # Update shared data
            shared_data.update({
                'x': x,
                'y': y,
                'z': z,
                'magnitude': magnitude,
                'steps': step_count,
                'posture': posture,
                'inactive_seconds': inactive_seconds,
                'pitch': pitch,
                'roll': roll
            })
            
            # Print current status (less frequent to reduce spam)
            if int(time.time()) % 10 == 0:  # Print every 10 seconds
                print(f"Steps: {step_count}, Posture: {posture}, Inactive: {inactive_seconds}s, Mag: {magnitude:.3f}")
            
        except Exception as e:
            print(f"Error in accelerometer monitoring: {e}")
        
        time.sleep(0.1)

def show_temp_humidity_display(dht_instance):
    """Show temperature and humidity with menu options"""
    global lcd
    
    result = dht_instance.read()
    
    if result.is_valid():
        temp_str = f"T:{result.temperature}C H:{result.humidity}%"
        lcd.lcd_clear()
        time.sleep(0.1)
        lcd.lcd_display_string(temp_str, 1)
        time.sleep(0.1)
        lcd.lcd_display_string("1.Eaten 2.Walked", 2)
    else:
        lcd.lcd_clear()
        time.sleep(0.1)
        lcd.lcd_display_string("Sensor Error!", 1)
        time.sleep(0.1)
        lcd.lcd_display_string("1.Eaten 2.Walked", 2)
    return result

def knowthembetter():
    global lcd
    lcd.lcd_clear()
    time.sleep(0.1)
    lcd.lcd_display_string("Rate ur feeling", 1)
    time.sleep(0.1)
    lcd.lcd_display_string("from 1-9", 2)
    
    # Wait for feeling rating with timeout
    try:
        keyvalue = shared_keypad_queue.get(timeout=10)  # 10 second timeout
        if 1 <= keyvalue <= 9:
            return keyvalue
        else:
            return 5  
    except queue.Empty:
        return 5  

def ending_speech():
    global lcd
    lcd.lcd_clear()
    time.sleep(0.1)
    lcd.lcd_display_string("Have a nice day!", 1)
    time.sleep(2)

def write_data_to_csv(timestamp, temperature, humidity, user_status, user_feeling, steps, x, y, z, magnitude, posture, distance=None, person_present=False):
    filename = "combined_monitoring_data.csv"
    file_exists = os.path.isfile(filename)
    
    with open(filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        
        if not file_exists:
            writer.writerow(['Timestamp', 'Temperature', 'Humidity', 'User_Status', 'User_Feeling', 
                           'Steps', 'X_Axis', 'Y_Axis', 'Z_Axis', 'Magnitude', 'Posture', 'Distance_cm', 'Person_Present'])
      
        writer.writerow([timestamp, temperature, humidity, user_status, user_feeling, 
                        steps, x, y, z, magnitude, posture, distance, person_present])
    
    print("Data saved to CSV")

def main():
    global lcd
    lcd = I2C_LCD_driver.lcd()
    dht_instance = dht11.DHT11(pin=21)
    
    # Initialize keypad
    keypad.init(key_pressed)
    time.sleep(0.5)
    
    # Start keypad thread
    keypad_thread = Thread(target=keypad.get_key)
    keypad_thread.daemon = True
    keypad_thread.start()
    time.sleep(0.5)
    
    # Reset daily data if new day
    reset_daily_data_if_new_day()
    
    # Shared data between threads
    shared_data = {
        'running': True,
        'x': 0, 'y': 0, 'z': 0,
        'magnitude': 0,
        'steps': 0,
        'posture': 'Unknown',
        'inactive_seconds': 0,
        'distance': None,
        'person_present': False,
        'absence_duration': 0,
        'waiting_for_checkin': False,
        'next_checkin_in': 0,
        'last_user_interaction': 0,
        'dht_instance': dht_instance
    }
    
    # Start accelerometer monitoring thread
    accel_thread = Thread(target=accelerometer_monitoring_thread, args=(shared_data,))
    accel_thread.daemon = True
    accel_thread.start()
    
    # Start ultrasonic sensor monitoring thread
    ultrasonic_thread = Thread(target=ultrasonic_monitoring_thread, args=(shared_data,))
    ultrasonic_thread.daemon = True
    ultrasonic_thread.start()
    
    # Start scheduled check-in thread
    checkin_thread = Thread(target=scheduled_checkin_thread, args=(shared_data,))
    checkin_thread.daemon = True
    checkin_thread.start()
    
    temp_update_counter = 0
    last_thingspeak_upload = 0
    thingspeak_interval = 20  # Upload to ThingSpeak every 20 seconds
    
    print("Enhanced monitoring system started!")
    print("Features: Temperature/Humidity, Accelerometer, Ultrasonic Sensor, Scheduled Check-ins, Daily Summary")
    print("Press 1 for 'Eaten', 2 for 'Walked', 3 to show current stats, 4 for sensor status, 5 for daily summary")
    
    try:
        while True:
            # Update temperature/humidity display every 10 iterations (unless waiting for check-in)
            if temp_update_counter % 10 == 0 and not shared_data['waiting_for_checkin']:
                tempandhumi = show_temp_humidity_display(dht_instance)
            temp_update_counter += 1
            
            # Check for keypad input
            try:
                keyvalue = shared_keypad_queue.get(timeout=0.5)
                print(f"Key pressed: {keyvalue}")
                
                # Update last user interaction time
                shared_data['last_user_interaction'] = time.time()
                
                if keyvalue == 1: 
                    print("User has eaten")
                    condition = "eaten"
                    user_status = 1
                    daily_data['eaten_count'] += 1
                    
                    feeling = knowthembetter()
                    daily_data['feeling_ratings'].append(feeling)
                    print("Feeling rating:", feeling)
                    time.sleep(1)
                    ending_speech()
                    
                    # Send telegram message
                    telegram_msg = f"User feeling: {feeling}/9, Activity: {condition}, Steps today: {shared_data['steps']}"
                    if shared_data['distance'] is not None:
                        telegram_msg += f", Distance: {shared_data['distance']}cm"
                    send_telegram_message(telegram_msg)
                    
                    # Get current sensor data
                    tempandhumi = show_temp_humidity_display(dht_instance)
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Write to CSV
                    write_data_to_csv(
                        timestamp, 
                        tempandhumi.temperature if tempandhumi.is_valid() else 0,
                        tempandhumi.humidity if tempandhumi.is_valid() else 0,
                        condition, feeling,
                        shared_data['steps'], shared_data['x'], shared_data['y'], shared_data['z'],
                        shared_data['magnitude'], shared_data['posture'],
                        shared_data['distance'], shared_data['person_present']
                    )
                    
                    # Upload to ThingSpeak
                    upload_to_thingspeak(
                        tempandhumi.temperature if tempandhumi.is_valid() else 0,
                        tempandhumi.humidity if tempandhumi.is_valid() else 0,
                        shared_data['steps'], shared_data['x'], shared_data['y'], shared_data['z'],
                        shared_data['magnitude'], feeling, shared_data['distance']
                    )
                    
                elif keyvalue == 2:
                    print("User has walked")
                    condition = "walked"
                    user_status = 2
                    daily_data['walked_count'] += 1
                    
                    feeling = knowthembetter()
                    daily_data['feeling_ratings'].append(feeling)
                    print("Feeling rating:", feeling)
                    time.sleep(1)
                    ending_speech()
                    
                    # Send telegram message
                    telegram_msg = f"User feeling: {feeling}/9, Activity: {condition}, Steps today: {shared_data['steps']}"
                    if shared_data['distance'] is not None:
                        telegram_msg += f", Distance: {shared_data['distance']}cm"
                    send_telegram_message(telegram_msg)
                    
                    # Get current sensor data
                    tempandhumi = show_temp_humidity_display(dht_instance)
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Write to CSV
                    write_data_to_csv(
                        timestamp,
                        tempandhumi.temperature if tempandhumi.is_valid() else 0,
                        tempandhumi.humidity if tempandhumi.is_valid() else 0,
                        condition, feeling,
                        shared_data['steps'], shared_data['x'], shared_data['y'], shared_data['z'],
                        shared_data['magnitude'], shared_data['posture'],
                        shared_data['distance'], shared_data['person_present']
                    )
                    
                    # Upload to ThingSpeak
                    upload_to_thingspeak(
                        tempandhumi.temperature if tempandhumi.is_valid() else 0,
                        tempandhumi.humidity if tempandhumi.is_valid() else 0,
                        shared_data['steps'], shared_data['x'], shared_data['y'], shared_data['z'],
                        shared_data['magnitude'], feeling, shared_data['distance']
                    )
                    
                elif keyvalue == 3:
                    # Display current statistics
                    lcd.lcd_clear()
                    time.sleep(0.1)
                    lcd.lcd_display_string(f"Steps: {shared_data['steps']}", 1)
                    time.sleep(0.1)
                    lcd.lcd_display_string(f"Posture: {shared_data['posture'][:16]}", 2)
                    time.sleep(3)
                    
                elif keyvalue == 4:
                    # Display sensor status
                    lcd.lcd_clear()
                    time.sleep(0.1)
                    if shared_data['distance'] is not None:
                        presence = "Yes" if shared_data['person_present'] else "No"
                        lcd.lcd_display_string(f"Dist:{shared_data['distance']:.1f}cm", 1)
                        time.sleep(0.1)
                        lcd.lcd_display_string(f"Present: {presence}", 2)
                    else:
                        lcd.lcd_display_string("Ultrasonic Error", 1)
                        time.sleep(0.1)
                        lcd.lcd_display_string("Sensor offline", 2)
                    time.sleep(3)
                    
                elif keyvalue == 5:
                    # Display daily summary
                    display_daily_summary()
                    
                temp_update_counter = 0
                
            except queue.Empty:
                # No key pressed, continue monitoring
                pass
            
            # Periodic ThingSpeak upload (every 20 seconds) with current sensor data
            current_time = time.time()
            if current_time - last_thingspeak_upload > thingspeak_interval:
                tempandhumi = show_temp_humidity_display(dht_instance)
                
                # Upload background monitoring data
                upload_success = upload_to_thingspeak(
                    tempandhumi.temperature if tempandhumi.is_valid() else 0,
                    tempandhumi.humidity if tempandhumi.is_valid() else 0,
                    shared_data['steps'], shared_data['x'], shared_data['y'], shared_data['z'],
                    shared_data['magnitude'], 5,  # Default feeling when no user interaction
                    shared_data['distance']
                )
                
                if upload_success:
                    print("Periodic data uploaded to ThingSpeak")
                
                last_thingspeak_upload = current_time
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nShutting down monitoring system...")
        shared_data['running'] = False
        
    except Exception as e:
        print(f"Error in main loop: {e}")
        shared_data['running'] = False
    
    finally:
        GPIO.cleanup()


if _name_ == '_main_':
    main()