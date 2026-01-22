import time, json
from time import sleep
from umqtt.simple import MQTTClient
import random
import ubinascii
from machine import unique_id
from machine import Pin

import network
import time

def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect("PrettyFlyWifi", "CrystalMettIstCool32!")

    while not wlan.isconnected():
        print("Connecting to WiFi...")
        time.sleep(0.5)

    print("WiFi connected:", wlan.ifconfig())

wifi_connect()

green = Pin(2, Pin.OUT)
yellow = Pin(3, Pin.OUT)
red = Pin(4, Pin.OUT)
blue = Pin(5, Pin.OUT)

colorMap = {
    "g" : green,
    "y" : yellow,
    "r": red,
    "b": blue,
}


failure = Pin(17, Pin.OUT)
success = Pin(16, Pin.OUT)

lights = ['g', 'y', 'r', 'b']

BROKER = "broker.hivemq.com"
TOPIC_SUB = b"sketchingwithhardwareGI/json"

client_id_sub = b"sub_" + ubinascii.hexlify(unique_id())

G_KEY = [random.choice(lights) for _ in range(5)]

failure.on()

def generate_key():
    global G_KEY
    G_KEY = [random.choice(lights) for _ in range(5)]

def show_key(key):
    for color in key:
        colorMap[color].on()
        sleep(0.5)
        colorMap[color].off()
        sleep(0.1)

def on_message(topic, msg):
    print("RAW:", topic, msg)
    try:
        data = json.loads(msg)
        print(data)
        print("JSON decoded:", data)
        sleep(0.2)
        if (data["generate_global_key"]):
            failure.on()
            success.off()
            generate_key()
            show_key(G_KEY)
            print(G_KEY)
        else:
            print(data['colors'])
            #Enter key for access
            if ((data['colors']==G_KEY)):
                failure.off()
                success.on()
            else:
                failure.on()
                success.off()
        



    except Exception as e:
        failure.on()
        success.off()
        print("Invalid JSON:", e)


def start_subscriber():
    global client

    client = MQTTClient(client_id_sub, BROKER, keepalive=30)
    client.set_callback(on_message)

    while True:
        try:
            print("Connecting to broker...")
            client.connect()
            client.subscribe(TOPIC_SUB)
            print("Subscribed to:", TOPIC_SUB)
            break
        except Exception as e:
            failure.on()
            success.off()
            print("Connection error:", e)
            time.sleep(3)

    # Non-blocking loop
    while True:
        try:
            client.check_msg()
        except OSError:
            print("Lost connection… retrying.")
            client.disconnect()
            time.sleep(2)
            return  # break out & reset the program OR reconnect in a loop

        time.sleep(0.1)


start_subscriber()
