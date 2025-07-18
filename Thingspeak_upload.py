import RPi.GPIO as GPIO
from time import sleep
import Adafruit_DHT
import requests #see http://docs.python-requests.org/en/master for more details

sensor = Adafruit_DHT.AM2302
pin = 4 #GPIO 4 or pin 7
myUploadAPI = "_____________________" #modify this to yours
baseURL = 'https://api.thingspeak.com/update?api_key=%s' %myUploadAPI

while(True):
    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

    if humidity is not None and temperature is not None:
        print('Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(temperature, humidity))
        resp = requests.get(_____________________________________________________) #upload to Thingspeak

    else:
        print('Failed to get reading. Try again!')
    sleep(15) #limit to upload rate, for free channel



    
