import serial
import json

def send_json():
    JsonVar = {
        "kp": 1.0,
        "ki": 0.1,
        "kd": 0.05,
        "sp": 0,
        "mode": False,
        "button": 2
    }

    try:
        with serial.Serial('COM4', 115200, timeout=1) as ser:
            # Convertir a string JSON
            json_string = json.dumps(JsonVar)

            # Enviar (IMPORTANTE agregar \n)
            ser.write((json_string + '\n').encode())

            print("Enviado:", json_string)

    except serial.SerialException as e:
        print(f"Error al abrir el puerto serial: {e}")


if __name__ == "__main__":
    send_json()

""""
import serial

tempoarlList = []

def read_from_serial():
    ser = serial.Serial('COM4', 115200, timeout=1)
    try:
        while True:
            position = ser.readline().decode().strip()
            tempoarlList.append(position)

            if len(tempoarlList) > 11:
                try:
                    print(float(position))
                except ValueError:
                    continue  # ignora datos inválidos
                tempoarlList.pop(0)

    except serial.SerialException as e:
        print(f"Error al abrir el puerto serial: {e}")
    finally:
        ser.close()

if __name__ == "__main__":
    read_from_serial()
"""