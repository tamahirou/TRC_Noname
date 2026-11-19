# pip install paho-mqtt
import paho.mqtt.client as mqtt

BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC = "pico_bg96_gnss001/data"  # Pico側と同じトピック名にする


def on_connect(client, userdata, flags, rc):
    print("Connected with result code", rc)
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    print("[{}] {}".format(msg.topic, msg.payload.decode()))


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_forever()