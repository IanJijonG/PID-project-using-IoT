import serial
import json

def main():
    JsonVar = {
        "kp": 1.0,
        "ki": 0.1,
        "kd": 0.05,
        "sp": 10,
        "mode": True,
        "button": 2
    }

    try:
        with serial.Serial('COM4', 115200, timeout=1) as ser:
            print("Conectado...\n")

            while True:
                # 📤 Enviar JSON
                json_string = json.dumps(JsonVar)
                ser.write((json_string + '\n').encode())
                print("Enviado:", json_string)

                # 📥 Leer 3 valores (cada uno en una línea)
                line1 = ser.readline().decode(errors='ignore').strip()
                line2 = ser.readline().decode(errors='ignore').strip()
                line3 = ser.readline().decode(errors='ignore').strip()

                if line1 and line2 and line3:
                    try:
                        v1 = float(line1)
                        v2 = float(line2)
                        v3 = float(line3)

                        print(f"Recibido -> {v1}, {v2}, {v3}")

                    except ValueError:
                        print("Datos inválidos:", line1, line2, line3)

    except serial.SerialException as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()