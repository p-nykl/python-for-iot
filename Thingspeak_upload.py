import requests

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
    except Exception as e:
        print(f"Exception during upload: {e}")
