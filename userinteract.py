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

shared_keypad_queue = queue.Queue()
lcd = None

def key_pressed(key):
    shared_keypad_queue.put(key)

GPIO.setmode(GPIO.BCM)
    
def main():
    global lcd
    
    # Initialize components once
    lcd = I2C_LCD_driver.lcd()
    instance = dht11.DHT11(pin=21)
    
    keypad.init(key_pressed)
    time.sleep(0.5)
        
    keypad_thread = Thread(target=keypad.get_key)
    keypad_thread.daemon = True
    keypad_thread.start()
    time.sleep(0.5)

    temp_update_counter = 0
    
    while True:
        # Update temperature display every 10 loops (about 5 seconds)
        if temp_update_counter % 10 == 0:
            show_temp_humidity_display(instance)
        temp_update_counter += 1
        
        # Check if there's keypad input (non-blocking)
        try:
            keyvalue = shared_keypad_queue.get(timeout=0.5)  # Check every 0.5 seconds
            print("key value ", keyvalue)
                
            if keyvalue == 1: 
                print("Eaten")
                condition = "eaten"
            elif keyvalue == 2:
                print("Walked")
                condition = "walked"
            else:
                continue  # Invalid key, go back to temp display
                
            feeling = knowthembetter()
            print("Feeling rating:", feeling)
            time.sleep(1)
            ending_speech()
            time.sleep(2)
            send_telegram_message(feeling, condition)
            
            # Reset counter after user interaction
            temp_update_counter = 0
            
        except queue.Empty:
            # No keypad input, continue loop
            continue

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
            return 5  # Default if invalid
    except queue.Empty:
        return 5  # Default if no input

def ending_speech():
    global lcd
    lcd.lcd_clear()
    time.sleep(0.1)
    lcd.lcd_display_string("Have a nice day", 1)
    time.sleep(2)

def send_telegram_message(feeling, condition):
    try:
        TELEGRAM_BOT_TOKEN = '7885273126:AAEpr5Dy9bUXYE3kf9lEH1ww2bXsByE9y5c'
        TELEGRAM_CHAT_ID = '6101168212'
        message = f"User feeling: {feeling}, Condition: {condition}"
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, data=data, timeout=5)
        print("Telegram message sent successfully")
    except Exception as e:
        print(f"Failed to send telegram message: {e}")

if __name__ == '__main__':
    main()