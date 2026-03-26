from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import time
import serial

app = Flask(__name__)
socketio = SocketIO(app)

temporalList = []

def connectionSerial():

    try:
        ser = serial.Serial('COM4', 115200)
        return ser
    
    except serial.SerialException as e:
        print(f"Error al abrir el puerto serial: {e}")
        return None
    
ser = connectionSerial()

@app.route("/")
def helloWorld():
    nombre = "HMI"
    return render_template("HMIv2.html",nombre=nombre)

@socketio.on("connect")
def handle_connect():
    print("Cliente conectado")

# Desconexión
@socketio.on("disconnect")
def handle_disconnect():
    print("Cliente desconectado")

@socketio.on("command")
def handle_command(data):
    dataName = data.get("cmd")
    print(f"Comando recibido: {dataName}")

    if dataName == "start":
        print("Iniciar proceso")


def read_from_serial():
    try:
        while True:
            position = ser.readline().decode().strip()
            temporalList.append(position)

            if len(temporalList) > 11:
                print(float(position))
                temporalList.pop(0)

    except serial.SerialException as e:
        print(f"Error al abrir el puerto serial: {e}")



def send_data():
    index = 0
    while True:
        index += 1
        
        position = read_from_serial()
        socketio.emit("data", {
            "position": position,
        })

        time.sleep(1)

def commandFilter(command):
    if command == "manual":
        print("Modo manual activado")

threading.Thread(target=send_data, daemon=True).start()


if __name__ == "__main__":
    socketio.run(app, debug=True)

