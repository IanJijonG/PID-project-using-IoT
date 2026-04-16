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
        print("Error al detectar puertos")
        print(result.stderr)
        return None, None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Error leyendo JSON de Arduino CLI")
        return None, None
    
    for item in data:
        if (
            item.get("port")
            and item["port"].get("address")
            and item.get("matching_boards")
        ):
            puerto = item["port"]["address"]
            fqbn = item["matching_boards"][0].get("fqbn")

            return puerto, fqbn

    return None, None

def connectionSerial():

    try:
        puerto, fqbn = detectar_puerto()
        ser = serial.Serial(puerto, 115200)
        ser.timeout = 0
        return ser,fqbn
    
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
"""
def read_from_serial(ser):
    try:
        while True:
            # Leer tres líneas consecutivas
            line1 = ser.readline().decode(errors='ignore').strip()
            line2 = ser.readline().decode(errors='ignore').strip()
            line3 = ser.readline().decode(errors='ignore').strip()

            try:
                val1 = float(line1)
                val2 = float(line2)
                val3 = float(line3)

                

                if len(temporalList) < 11:
                    temporalList.append((val1, val2, val3))
                else:
                    print(val1, val2, val3)

            except ValueError:
                print(f"Datos inválidos: {line1}, {line2}, {line3}")

    except serial.SerialException as e:
        print(f"Error al abrir el puerto serial: {e}")
"""""


def writeJsonSerial(ser,data):

    try:
        json_str = json.dumps(data) + '\n'
        ser.write(json_str.encode('utf-8'))

    except serial.SerialException as e:
        print(f"Error al enviar JSON: {e}")
