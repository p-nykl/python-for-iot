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

shared_keypad_queue = queue.Queue()
lcd = None

def key_pressed(key):
    shared_keypad_queue.put(key)

GPIO.setmode(GPIO.BCM)
    
def main():
    global lcd
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
        if temp_update_counter % 10 == 0:
            tempandhumi= show_temp_humidity_display(instance)
        temp_update_counter += 1
        
        keyvalue = shared_keypad_queue.get()# Check every 0.5 seconds
        print("key value ", keyvalue)
            
        if keyvalue == 1: 
            print("Eaten")
            condition = "eaten"
            user_status=1
        elif keyvalue == 2:
            print("Walked")
            condition = "walked"
            user_status=2
        else:
            continue  
            
        feeling = knowthembetter()
        print("Feeling rating:", feeling)
        time.sleep(1)
        ending_speech()
        time.sleep(2)
        send_telegram_message(feeling, condition)
     
        temp_update_counter = 0

        temp = []
        humi= []
        user_status = []
        user_feeling=[]
        temp.append(tempandhumi.temperature)
        humi.append(tempandhumi.humidity)
        user_status.append(condition)
        user_feeling.append(feeling)
        print(user_status)
        
        write_data_to_csv(temp, humi, user_status, user_feeling)
        

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

def send_telegram_message(feeling, condition):
    TELEGRAM_BOT_TOKEN = '7885273126:AAEpr5Dy9bUXYE3kf9lEH1ww2bXsByE9y5c'
    TELEGRAM_CHAT_ID = '6101168212'
    message = f"User feeling: {feeling}, Condition: {condition}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, data=data, timeout=5)
    print("Telegram message sent successfully")


def write_data_to_csv(temperature, humidity, user_status, user_feeling):
    filename = "sensor_and_userinteraction_data.csv"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    file_exists = os.path.isfile(filename)
    
    with open(filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        
        if not file_exists:
            writer.writerow(['Timestamp', 'Temperature', 'Humidity', 'User_Status', 'User_Feeling'])
      
        writer.writerow([timestamp, temperature, humidity, user_status, user_feeling])
    
    print("Data saved")
        

def send_thingspeak():
    temp=[]
    humi=[]
    user_data=[]
    user_feeling=[]
    with open("sensor_and_userinteraction_data.csv","r",newline="") as csvfile:
        data=csv.reader(csvfile,delimiter=',')
        next(data)

        for row in data:
            if len(data)>=5: #one more is for timestamp-row[0]
                temp.append(int(row[1]))
                humi.append(int(row[2]))
                user_data.append(int(row[3]))
                user_feeling.append(int(row[4]))
    

    for x in range(len(data)):
        print("send thingspeak loop")
        resp=requests.get("https://api.thingspeak.com/update?api_key=AVURSRXZ07INDOZO&field1={temp[x]}&field2={humi[x]}&field3={user_data[x]}&field 4={user_feeling[x]}" )
        time.sleep(20)

if __name__ == '__main__':
    main()
