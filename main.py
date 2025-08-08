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
from datetime import date

# Shared components
shared_keypad_queue = queue.Queue()
lcd = None

# Accelerometer mock class (use real adxl345 if available)
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

def key_pressed(key):
    shared_keypad_queue.put(key)

GPIO.setmode(GPIO.BCM)

def upload_to_thingspeak(temperature, humidity, steps, x, y, z, magnitude, user_feeling):
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
    return math.sqrt(x**2 + y**2 + z**2)

def detect_fall(prev_magnitude, curr_magnitude, threshold=0.1):
    if prev_magnitude is None:
        return False
    diff = abs(curr_magnitude - prev_magnitude)
    time.sleep(5)  # Simulate processing delay
    print(f"Magnitude: {curr_magnitude:.5f}, Prev: {prev_magnitude:.5f}, Diff: {diff:.5f}")
    return diff > threshold

def accelerometer_monitoring_thread(shared_data):
    """Thread for continuous accelerometer monitoring"""
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
    fall_cooldown_seconds = 10
    
    print("Accelerometer monitoring started...")
    
    while shared_data['running']:
        try:
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
            current_time = time.time()
            if detect_fall(prev_magnitude, magnitude):
                if current_time - last_fall_time > fall_cooldown_seconds:
                    fall_message = "⚠️ FALL DETECTED! Elderly person may need immediate assistance!"
                    print(fall_message)
                    send_telegram_message(fall_message)
                    last_fall_time = current_time
            
            prev_magnitude = magnitude
            
            # Inactivity alert
            if inactive_seconds > 300:  # 5 minutes of inactivity
                inactivity_message = f"⚠️ No movement detected for {inactive_seconds} seconds. Please check on the elderly person."
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
                'inactive_seconds': inactive_seconds
            })
            
            # Print current status (less frequent to reduce spam)
            if int(time.time()) % 5 == 0:  # Print every 5 seconds
                print(f"Steps: {step_count}, Posture: {posture}, Inactive: {inactive_seconds}s")
            
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

def write_data_to_csv(timestamp, temperature, humidity, user_status, user_feeling, steps, x, y, z, magnitude, posture):
    filename = "combined_monitoring_data.csv"
    file_exists = os.path.isfile(filename)
    
    with open(filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        
        if not file_exists:
            writer.writerow(['Timestamp', 'Temperature', 'Humidity', 'User_Status', 'User_Feeling', 
                           'Steps', 'X_Axis', 'Y_Axis', 'Z_Axis', 'Magnitude', 'Posture'])
      
        writer.writerow([timestamp, temperature, humidity, user_status, user_feeling, 
                        steps, x, y, z, magnitude, posture])
    
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
    
    # Shared data between threads
    shared_data = {
        'running': True,
        'x': 0, 'y': 0, 'z': 0,
        'magnitude': 0,
        'steps': 0,
        'posture': 'Unknown',
        'inactive_seconds': 0
    }
    
    # Start accelerometer monitoring thread
    accel_thread = Thread(target=accelerometer_monitoring_thread, args=(shared_data,))
    accel_thread.daemon = True
    accel_thread.start()
    
    temp_update_counter = 0
    last_thingspeak_upload = 0
    thingspeak_interval = 20  # Upload to ThingSpeak every 20 seconds
    
    print("Combined monitoring system started!")
    print("Press 1 for 'Eaten', 2 for 'Walked', 3 to show current stats")
    

    while True:
        # Update temperature/humidity display every 10 iterations
        if temp_update_counter % 10 == 0:
            tempandhumi = show_temp_humidity_display(dht_instance)
        temp_update_counter += 1
        
        # Check for keypad input
        
        keyvalue = shared_keypad_queue.get(timeout=0.5)
        print(f"Key pressed: {keyvalue}")
            
        if keyvalue == 1: 
            print("User has eaten")
            condition = "eaten"
            user_status = 1
            
            feeling = knowthembetter()
            print("Feeling rating:", feeling)
            time.sleep(1)
            ending_speech()
            
            # Send telegram message
            telegram_msg = f"User feeling: {feeling}/9, Activity: {condition}, Steps today: {shared_data['steps']}"
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
                shared_data['magnitude'], shared_data['posture']
            )
            
            # Upload to ThingSpeak
            upload_to_thingspeak(
                tempandhumi.temperature if tempandhumi.is_valid() else 0,
                tempandhumi.humidity if tempandhumi.is_valid() else 0,
                shared_data['steps'], shared_data['x'], shared_data['y'], shared_data['z'],
                shared_data['magnitude'], feeling
            )
                    
        elif keyvalue == 2:
            print("User has walked")
            condition = "walked"
            user_status = 2
            
            feeling = knowthembetter()
            print("Feeling rating:", feeling)
            time.sleep(1)
            ending_speech()
            
            # Send telegram message
            telegram_msg = f"User feeling: {feeling}/9, Activity: {condition}, Steps today: {shared_data['steps']}"
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
                shared_data['magnitude'], shared_data['posture']
            )
            
            # Upload to ThingSpeak
            upload_to_thingspeak(
                tempandhumi.temperature if tempandhumi.is_valid() else 0,
                tempandhumi.humidity if tempandhumi.is_valid() else 0,
                shared_data['steps'], shared_data['x'], shared_data['y'], shared_data['z'],
                shared_data['magnitude'], feeling
            )
            
        elif keyvalue == 3:
            # Display current statistics
            lcd.lcd_clear()
            time.sleep(0.1)
            lcd.lcd_display_string(f"Steps: {shared_data['steps']}", 1)
            time.sleep(0.1)
            lcd.lcd_display_string(f"Posture: {shared_data['posture'][:16]}", 2)
            time.sleep(3)
            
        temp_update_counter = 0
                
            
            
        # Periodic ThingSpeak upload (every 20 seconds) with current sensor data
        current_time = time.time()
        if current_time - last_thingspeak_upload > thingspeak_interval:
            tempandhumi = show_temp_humidity_display(dht_instance)
            
            # Upload background monitoring data
            upload_success = upload_to_thingspeak(
                tempandhumi.temperature if tempandhumi.is_valid() else 0,
                tempandhumi.humidity if tempandhumi.is_valid() else 0,
                shared_data['steps'], shared_data['x'], shared_data['y'], shared_data['z'],
                shared_data['magnitude'], 5  # Default feeling when no user interaction
            )
            
            if upload_success:
                print("Periodic data uploaded to ThingSpeak")
            
            last_thingspeak_upload = current_time
        
        time.sleep(0.1)

def summary_of_day():
    lcd=LCD.lcd()
    lcd.lcd_clear()
    time.sleep(0.1)

    today = date.today()
    print (today)

    today = datetime.now().strftime("%Y-%m-%d")  # Adjust format to match your timestamp format

    temp = []
    humi = []
    user_data = []
    user_feeling = []

    with open("sensor_and_userinteraction_data.csv", "r", newline="") as csvfile:
        data = csv.reader(csvfile, delimiter=',')
        next(data)  # Skip header row
        
        for row in data:
            if len(row) >= 5:  
                timestamp = row[0]
                row_date = timestamp.split()[0] 
                
                if row_date == today:
                    temp.append(int(row[1]))
                    humi.append(int(row[2]))
                    user_data.append(int(row[3]))
                    user_feeling.append(int(row[4]))

        if len(temp) > 0:  
            total_temp = sum(temp)  
            avg_temp = total_temp / len(temp)  
                
            total_humi = sum(humi)
            avg_humi = total_humi / len(humi)
        
            total_feeling = sum(user_feeling)
            avg_feeling = total_feeling / len(user_feeling)

            print(f"Today's date: {today}")
            lcd.lcd_display_string(f"Today's date: {today}", 1)

            print(f"Average Temperature: {avg_temp:.2f}")
            lcd.lcd_display_string(f"Average Temperature: {avg_temp:.2f}", 1)

            print(f"Average Humidity: {avg_humi:.2f}")
            lcd.lcd_display_string(f"Average Humidity: {avg_humi:.2f}", 1)
        
            
            #analyse of user's average feeling of the day
            if user_feeling>=7:
                print("Today is Great!",1)
                lcd.lcd_display("Today is Great!", 1)
                time.sleep(0.5)
            
            elif user_feeling>=4:
                print("Today is okay...",1)
                lcd.lcd_display("Today is okay...", 1)
                time.sleep(0.5)

            else:
                print("Maybe tomorrow is better")
                lcd.lcd_display("Maybe tomorrow", 1)
                lcd.lcd_display("is better", 2)
      

if __name__ == '__main__':
    main()