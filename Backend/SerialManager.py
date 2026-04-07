import serial
import json

temporalList = []

def connectionSerial():

    try:
        ser = serial.Serial('COM4', 115200)
        return ser
    
    except serial.SerialException as e:
        print(f"Error al abrir el puerto serial: {e}")
        return None

def reconnect_serial():
    global ser

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
        return None

def writeJsonSerial(ser, data):
    try:
        json_str = json.dumps(data) + '\n'
        ser.write(json_str.encode('utf-8'))
    except:
        return None