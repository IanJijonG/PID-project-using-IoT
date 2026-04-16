from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import time
import serial

app = Flask(__name__)
socketio = SocketIO(app)

positionExample = [1, 2, 5, 10, 15, 20, 25, 21, 30, 30]
positionArray = []

language = ""

def readPosFromSerial():
    ser = serial.Serial('COM3', 115200)
    while True:
        line = ser.readline().decode().strip()
        if line:
            position = int(line)
            positionArray.append(position)



@app.route("/")
def helloWorld():
    nombre = "HMI"
    return render_template("HMIv2.html",nombre=nombre)

@socketio.on("connect")
def handle_connect():
    print("Cliente conectado")

@socketio.on("disconnect")
def handle_disconnect():
    print("Cliente desconectado")

@socketio.on("command")
def handle_command(data):
    dataName = data.get("cmd")
    print(f"Comando recibido: {dataName}")

    if dataName == "start":
        print("Iniciar proceso")


def send_data():
    index = 0
    while True:
        index += 1

        socketio.emit("data", {
            "position": positionExample[index-1],
        })

        if index >= len(positionExample):
            index = 0

        time.sleep(1)

def commandFilter(command):
    if command == "manual":
        print("Modo manual activado")

threading.Thread(target=send_data, daemon=True).start()


if __name__ == "__main__":
    socketio.run(app, debug=True)