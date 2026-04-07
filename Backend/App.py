from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import time
import subprocess
import DBConnection as DBConn
import queue
import SerialManager as serialM

app = Flask(__name__)
socketio = SocketIO(app)
pidJson = {"kp":0, "ki":0, "kd": 0}

currentMode = 0
setpointJson = {"sp":0}
modeJson = {"mode":0}

temporalList = []



QUEUE_MAX = 3000
DB_BATCH_SIZE = 100
db_queue = queue.Queue(QUEUE_MAX)


FQBN = "arduino:avr:uno"
PROYECTO = "ArduinoCodes"




@app.route("/")
def Rederizer():
    nombre = "HMI"
    return render_template("HMIv2.html",nombre=nombre)

@socketio.on("connect")
def handle_connect():
    global ser
    ser = serialM.connectionSerial()
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

def run_commandCLI(cmd):
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("---- ERROR ----")
        print(result.stderr.strip())
        print("---- OUTPUT ----")
        print(result.stdout.strip())
        return False


def send_data_Fronted():
    index = 0
    while True:
        index += 1
        
        position = serialM.read_from_serial()
        socketio.emit("data", {
            "position": position,
        })

        if not db_queue.full():
            db_queue.put(position)

        time.sleep(0.5)

def commandFilter(command,action,data):
    global setpointVar, currentMode

    if command == "manual" and action != "-":
        print("Modo manual activado")
        if action == "stop":
            print("stop")
            modeJson["mode"] = "stop"
            serialM.writeJsonSerial(ser,modeJson)

        elif action == "start":
            modeJson["mode"] = "start"
            serialM.writeJsonSerial(ser,modeJson)
            print("start")

        elif action == "reset":
            modeJson["mode"] = "reset"
            serialM.writeJsonSerial(ser,modeJson)
            print("reset")

    elif command == "pid" and action == "-":
        pidJson["kp"] = data.get("kp")
        pidJson["ki"] = data.get("ki")
        pidJson["kd"] = data.get("kd")

        print(pidJson)

        serialM.writeJsonSerial(ser,pidJson)
    
    elif command == "setpoint":
        setpointVar = float(action)
        print( setpointVar)
        setpointJson["sp"] = setpointVar

        serialM.writeJsonSerial(ser,setpointJson)
    

    elif command == "control_mode":
        currentMode= data.get("mode")


def DbWorker():
    DBConn.init_db()

    while True:
        try:
            item = db_queue.get(timeout=1)
        except queue.Empty:
            continue

        lote = [item]

        while not db_queue.empty() and len(lote) < DB_BATCH_SIZE:
            try:
                lote.append(db_queue.get_nowait())
            except queue.Empty:
                break

        DBConn.save_position(lote)

        for _ in lote:
            db_queue.task_done()

threading.Thread(target=DbWorker,daemon=True).start()

threading.Thread(target=send_data_Fronted, daemon=True).start()


if __name__ == "__main__":
    socketio.run(app, debug=True)

