import serial
import json
import threading
import time 

temporalList = []
warmUp = 0
serial_lock = threading.Lock()
last_valid_time = 0


def connectionSerial():

    try:
        ser = serial.Serial('COM4', 115200)
        ser.timeout = 0
        return ser
    
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
