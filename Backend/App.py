from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import time
import serial
import json

app = Flask(__name__)
socketio = SocketIO(app)
pidJson = {"kp":0, "ki":0, "kd": 0}

currentMode = 0
setpointJson = {"sp":0}
modeJson = {"mode":0}

temporalList = []



def connectionSerial():

    try:
        ser = serial.Serial('COM4', 115200)
        return ser
    
    except serial.SerialException as e:
        print(f"Error al abrir el puerto serial: {e}")
        return None
    

@app.route("/")
def helloWorld():
    nombre = "HMI"
    return render_template("HMIv2.html",nombre=nombre)

@socketio.on("connect")
def handle_connect():
    global ser
    ser = connectionSerial()
    print("Cliente conectado")

@socketio.on("disconnect")
def handle_disconnect():
    ser.close()
    print("Cliente desconectado")

@socketio.on("command")
def handle_command(data):
    dataName = data.get("cmd")
    print(f"Comando recibido: {dataName}")

    if dataName == "pid":
        commandFilter(dataName,"-",data)
    elif dataName == "setpoint":
        commandFilter(dataName,data.get("value"),data)
    else:
        commandFilter(dataName,data.get("action"),data)


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

def commandFilter(command,action,data):
    global setpointVar, currentMode

    if command == "manual" and action != "-":
        print("Modo manual activado")
        if action == "stop":
            print("stop")
            modeJson["mode"] = "stop"
            writeJsonSerial(ser,modeJson)
        elif action == "start":
            modeJson["mode"] = "start"
            print("start")
        elif action == "reset":
            modeJson["mode"] = "reset"
            print("reset")

    elif command == "pid" and action == "-":
        pidJson["kp"] = data.get("kp")
        pidJson["ki"] = data.get("ki")
        pidJson["kd"] = data.get("kd")

        print(pidJson)

        writeJsonSerial(ser,pidJson)
    
    elif command == "setpoint":
        setpointVar = float(action)
        print( setpointVar)
        setpointJson["sp"] = setpointVar

        writeJsonSerial(ser,setpointJson)
    

    elif command == "control_mode":
        currentMode= data.get("mode")

def writeJsonSerial(ser, data):
    json_str = json.dumps(data) + '\n'
    ser.write(json_str.encode('utf-8'))
        
threading.Thread(target=send_data, daemon=True).start()


if __name__ == "__main__":
    socketio.run(app, debug=True)

