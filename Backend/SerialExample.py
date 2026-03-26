import serial

tempoarlList = []

def read_from_serial():
    ser = serial.Serial('COM4', 115200)
    try:
        while True:
            position = ser.readline().decode().strip()
            tempoarlList.append(position)

            if len(tempoarlList) > 11:
                print(float(position))
                tempoarlList.pop(0)



    except serial.SerialException as e:
        print(f"Error al abrir el puerto serial: {e}")



if __name__ == "__main__":

    value = read_from_serial()


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