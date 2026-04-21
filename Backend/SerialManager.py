import serial
import json
import threading
import time 
import subprocess

temporalList = []
warmUp = 0
serial_lock = threading.Lock()
last_valid_time = 0


def detectar_puerto():
    result = subprocess.run(
        ["arduino-cli", "board", "list", "--format", "json"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(result.stderr)
        return None, None, None

    data = json.loads(result.stdout)

    detected_ports = data.get("detected_ports", [])

    for item in detected_ports:
        port = item.get("port", {})
        address = port.get("address")

        # 🔥 placa (board) detectada
        board = item.get("matching_boards", [{}])[0] if item.get("matching_boards") else {}

        fqbn = board.get("fqbn")
        name = board.get("name")

        if address:
            print(f"✅ Puerto detectado: {address}")
            print(f"📟 Placa detectada: {name}")
            print(f"⚙️ FQBN: {fqbn}")

            return address, fqbn

    print("🛑 No se encontró ningún dispositivo")
    return None, None, None

def connectionSerial():

    port,FBQN,  = detectar_puerto()

    try:
        ser = serial.Serial(port, 115200)
        ser.timeout = 0
        return ser, FBQN
    
    except serial.SerialException as e:
        print(f"Error al abrir el puerto serial: {e}")
        return None

def reconnect_serial(ser):


    try:
        if ser:
            ser.close()
    except:
        pass

    ser = connectionSerial()

    if ser:
        print("Reconectado")
    else:
        print("Fallo reconexión")

import time

def read_from_serial(ser):
    global warmUp, temporalList, last_valid_time

    try:
        if ser is None or not ser.is_open:
            return None, None

        if ser.in_waiting <= 0:
            return None, None

        line = ser.readline().decode(errors='ignore').strip()

        if not line:
            return None, None

        temporalList.append(line)

        try:
            value = float(line)
        except ValueError:
            return None, None

        # warm-up
        if warmUp < 11:
            warmUp += 1
            return None, None

        now = time.time()

        interval = None
        if last_valid_time != 0:
            interval = now - last_valid_time

        last_valid_time = now

        return value, interval

    except Exception as e:
        print(f"Error serial: {e}")
        return None, None


def writeJsonSerial(ser,data):

    try:
        json_str = json.dumps(data) + '\n'
        ser.write(json_str.encode('utf-8'))

    except serial.SerialException as e:
        print(f"Error al enviar JSON: {e}")
