import serial
import json

temporalList = []
warmUp = 0

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

def read_from_serial(ser):
    global warmUp, temporalList

    try:
        if ser.in_waiting > 0:

            position = ser.readline().decode(errors='ignore').strip()

            if not position:
                return None

            try:
                temporalList.append(position)

                if warmUp < 11:
                    warmUp += 1
                    return None
                else:
                    return float(position)

            except ValueError:
                return None

        else:
            return None

    except Exception as e:
        print(f"Error serial: {e}")
        return None

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
    
