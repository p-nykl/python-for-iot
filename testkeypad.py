import keypad
import I2C_LCD_driver
from threading import Thread
import queue
import time

shared_keypad_queue = queue.Queue()
lcd = None

def key_pressed(key):
    shared_keypad_queue.put(key)
    
def main():
    global lcd
    
    try:
        # Initialize LCD first
        lcd = I2C_LCD_driver.lcd()
        time.sleep(0.5)  # Give LCD time to initialize
        
        # Then initialize keypad
        keypad.init(key_pressed)
        time.sleep(0.5)  # Give keypad time to initialize
        
        keypad_thread = Thread(target=keypad.get_key)
        keypad_thread.daemon = True
        keypad_thread.start()
        time.sleep(0.5)  # Let thread start properly

        while True:
            lcd.lcd_clear()
            time.sleep(0.1)  # Small delay after clear
            lcd.lcd_display_string("1.Eaten", 1)
            time.sleep(0.1)
            lcd.lcd_display_string("2.Walked", 2)
         
            keyvalue = shared_keypad_queue.get()
            print("key value ", keyvalue)
            
            if keyvalue == 1: 
                print("Eaten")
            elif keyvalue == 2:
                print("Walked")
            
            feeling = knowthembetter()
            print("Feeling rating:", feeling)
            time.sleep(1)
            ending_speech()
            time.sleep(2)
            
    except Exception as e:
        print(f"Error: {e}")

def knowthembetter():
    global lcd
    lcd.lcd_clear()
    time.sleep(0.1)
    lcd.lcd_display_string("Rate ur feeling", 1)
    time.sleep(0.1)
    lcd.lcd_display_string("from 1-9", 2)
    
    keyvalue = shared_keypad_queue.get()
    
    if 1 <= keyvalue <= 9:
        return keyvalue
    else:
        return 5

def ending_speech():
    global lcd
    lcd.lcd_clear()
    time.sleep(0.1)
    lcd.lcd_display_string("Have a nice day", 1)
    time.sleep(1)

if __name__ == '__main__':
    main()
