import I2C_LCD_driver 
import dht11
import time
import datetime
from time import sleep
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

def main():
    instance = dht11.DHT11(pin=21) #read data using pin 21
    LCD = I2C_LCD_driver.lcd()
    result = instance.read()
    read_dht(result)
    print("4")
    display_tempandhumi(result)

def read_dht(result):
    while True:
        if result.is_valid(): #print datetime & sensor values
            print("Temperature: %-3.1f C" % result.temperature)
            print("Humidity: %-3.1f %%" % result.humidity)
            time.sleep(0.5)
            return result
        sleep(1)

def display_tempandhumi(result):
    LCD = I2C_LCD_driver.lcd()  # instantiate an lcd object, call it LCD
    LCD.backlight(1)  # turn backlight on
    
    print("1")
    if result.is_valid():  # Check if the result is valid first
        temp_str = "Temp:" + str(result.temperature)
        humi_str = "Humi:" + str(result.humidity)
        LCD.lcd_display_string(temp_str + humi_str, 1)
        LCD.lcd_display_string("Press 1 to start", 2)
        print("2")
    else:
        LCD.lcd_display_string("Sensor Error!", 1)
        LCD.lcd_display_string("Check wiring", 2)
        print("3")
    
    time.sleep(2)
    return

if __name__ == '__main__':
    main()