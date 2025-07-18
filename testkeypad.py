import keypad
import I2C_LCD_driver
import Thread

shared_keypad_queue = queue.Queue()

def key_pressed(key):
    shared_keypad_queue.put(key)
    
def main():
    lcd = I2C_LCD_driver.lcd()
    keypad.init(key_pressed)
    keypad_thread = Thread(target=keypad.get_key)
    keypad_thread.start()

    while(True):
        lcd.lcd_clear()
        lcd.lcd_display_string("1.Eaten", 1)
        lcd.lcd_display_string("2.Walked", 2)
     
        keyvalue= shared_keypad_queue.get()

        print("key value ", keyvalue)
        

        if(keyvalue == 1): 
            feeling = knowthembetter(keyvalue)
            print(feeling)
           

        elif (keyvalue == 2):
            feeling = knowthembetter(keyvalue)
            print(feeling)

def knowthembetter(keyvalue):
    lcd = I2C_LCD_driver.lcd()
    lcd.lcd_display_string("Rate ur feeling", 1)
    lcd.lcd_display_string("from 1-9", 2)
    if(keyvalue == 1): 
            return 1

    elif (keyvalue == 2):
            return 2
    
    elif (keyvalue == 3):
            return 3

    elif (keyvalue == 4):
            return 4

    elif (keyvalue == 5):
            return 5

    elif (keyvalue == 6):
            return 6

    elif (keyvalue == 7):
            return 7

    elif (keyvalue == 8):
            return 8

    elif (keyvalue == 9):
            return 9


if __name__ == '__main__':
    main()