import paho.mqtt.client as mqtt
import json

BROKER = "test.mosquitto.org"
PORT = 1883
#USERNAME = "m07p6t1s7@mozmail.com"
#PASSWORD = "Db9aTJ~3'^dGf~8"
TOPIC = "kart/test"

def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected with reason code", reason_code)
    result, mid = client.subscribe(TOPIC, qos=1)
    print("Subscribed:", result)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        print("Battery SOC:", data["batterySOC"], "%")
        print("SystemFlags:", data["SystemFlags"])
        print("Speed:", data["Speed"])
    except (json.JSONDecodeError, KeyError) as e:
        print("Bad packet:", e)
        print(f"Received: {msg.payload.decode()}")

