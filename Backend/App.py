from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import time as t
import subprocess
import DBConnection as DBConn
import queue
import SerialManager as serialM
import CLIworker as cw



app = Flask(__name__)
socketio = SocketIO(app)
JsonVar = {"kp":1.0, "ki":0.1, "kd": 0.05,"sp":0,"mode":False,"button":2}
serial_lock = threading.Lock()

arduinoOriginalINO = "name.ino"

currentMode = 0

temporalList = []

last_serial_time = 0

intervalSer = 0 

ser = None

threads_started = False

QUEUE_MAX = 3000
DB_BATCH_SIZE = 100
db_queue = queue.Queue(QUEUE_MAX)
frontend_queue = queue.Queue(QUEUE_MAX)


fqbn = "arduino:avr:uno"
PROYECTO = "ArduinoCodes"


@app.route("/")
def Rederizer():
    nombre = "HMI"
    return render_template("HMIv2.html",nombre=nombre)

@socketio.on("connect")
def handle_connect():
    start_background_tasks()
    print("Cliente conectado")


def start_background_tasks():
    global threads_started, ser, fqbn

    if threads_started:
        return

    ser,fqbn = serialM.connectionSerial()
    
    InitialCodeCharger()
    socketio.start_background_task(serial_worker)
    socketio.start_background_task(send_data_Fronted)
    socketio.start_background_task(DbWorker)
    socketio.start_background_task(WatchDog)

    threads_started = True

@socketio.on("disconnect")
def handle_disconnect():
    global ser

    try:
        if ser and ser.is_open:
            ser.close()
    except:
        pass

@socketio.on("command")
def handle_command(data):
    dataName = data.get("cmd")
    print(f"Comando recibido: {dataName}")

    if dataName == "pid":
        commandFilter(dataName,"-",data)
    elif dataName == "setpoint":
        commandFilter(dataName,data.get("value"),data)
    elif dataName == "Code":
        commandFilter(dataName,data.get("code"),data)
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
    global ser, intervalSer
    buffer = []
    last_emit = t.time()

    while True:

        try:
            data = frontend_queue.get(timeout=0.1)
            buffer.append(data)
        except queue.Empty:
            pass

        if t.time() - last_emit >= 0.1:
            print(buffer)
            if buffer:
                socketio.emit("data", {
                    "positions": buffer
                })
                buffer = []
            last_emit = t.time()

        socketio.sleep(0.01)

def serial_worker():
    global ser, intervalSer

    while True:
        with serial_lock:
            position, intervalSer = serialM.read_from_serial(ser)

        if position is not None:
            try:
                position = float(position)

                # Cola para DB
                if not db_queue.full():
                    db_queue.put(position)

                # Cola para frontend
                if not frontend_queue.full():
                    frontend_queue.put(position)

            except:
                print("Dato inválido:", position)

        socketio.sleep(0.01)

    
def reconnect_serial():
    global ser

    try:
        with serial_lock:
            if ser:
                try:
                    ser.close()
                except:
                    pass

            print("Reintentando conexión serial...")

            ser = serialM.connectionSerial()

            if ser and ser.is_open:
                print("Serial reconectado correctamente")
                return True
            else:
                print("Fallo al reconectar serial")
                return False

    except Exception as e:
        print("Error en reconexión serial:", e)
        return False

def WatchDog():
    global intervalSer

    TIMEOUT = 2.0

    while True:
        socketio.sleep(0.5)

        if intervalSer is None:
            continue


        if intervalSer > TIMEOUT:
            print("Watchdog: sistema sin respuesta, reconectando...")
            reconnect_serial()
            intervalSer = None

def commandFilter(command,action,data):
    global setpointVar, currentMode, fqbn

    if command == "manual" and action != "-":
        print("Modo manual activado")

        if action == "stop":
            print("stop")
            JsonVar["button"] = 2

            UpdateJsonArduino()

        elif action == "start":
            JsonVar["button"] = 1
            print("start")

            UpdateJsonArduino()

        elif action == "reset":
            print("reset")
            JsonVar["button"] = 0
            UpdateJsonArduino()

    elif command == "pid" and action == "-":
        JsonVar["kp"] = data.get("kp")
        JsonVar["ki"] = data.get("ki")
        JsonVar["kd"] = data.get("kd")

        UpdateJsonArduino()

    elif command == "setpoint":
        setpointVar = float(action)
        print( setpointVar)
        JsonVar["sp"] = setpointVar

        UpdateJsonArduino()

    elif command == "control_mode":
        currentMode= data.get("mode")
        
        if currentMode == "velocity":
            JsonVar["mode"] = True
        else:
            JsonVar["mode"] = False
        print(currentMode)


        UpdateJsonArduino()
    
    elif command == "Code":
        code = data.get("code")
        port = serialM.detectar_puerto()
        print(code)

        cw.compile(fqbn,code)
        socketio.sleep(1)
        cw.Upload(fqbn,code,port)

def InitialCodeCharger():
    global arduinoOriginalINO

    try:
        port, FQBN = serialM.detectar_puerto()

        cw.compile(fqbn,arduinoOriginalINO)
        t.sleep(0.5)
        cw.Upload(FQBN,arduinoOriginalINO,port)

        return 1
    
    except:
        return 0
    



def UpdateJsonArduino():
    global JsonVar, ser

    print(JsonVar)

    if any(v is None for v in JsonVar.values()):
        print("Agrega valores válidos")
    else:
        with serial_lock:
            serialM.writeJsonSerial(ser, JsonVar)

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


if __name__ == "__main__":

    socketio.run(app, debug=True, use_reloader=False)

