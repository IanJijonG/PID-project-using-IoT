import subprocess
import json
import sys

FQBN = "arduino:avr:uno"
PROYECTO = "mi_proyecto"


def run_command(cmd):
    
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

    return True


def detectar_puerto():

    result = subprocess.run(
        ["arduino-cli", "board", "list", "--format", "json"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("zError al detectar puertos")
        print(result.stderr)
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Error leyendo JSON de Arduino CLI")
        return None
    
    for item in data:
        if (
            item.get("port")
            and item["port"].get("address")
            and item.get("matching_boards")
        ):
    
            return item["port"]["address"]




def main():
    print("🚀 Iniciando proceso Arduino\n")

    puerto = detectar_puerto()

    if not puerto:
        print("🛑 No se encontró ningún Arduino conectado")
        sys.exit(1)

    print(f"🔌 Puerto detectado: {puerto}")

    # Compilar
    if not run_command(
        ["arduino-cli", "compile", "--fqbn", FQBN, PROYECTO],
    ):
        sys.exit(1)

    # Subir
    if not run_command(
        ["arduino-cli", "upload", "-p", puerto, "--fqbn", FQBN, PROYECTO],
    ):
        sys.exit(1)

    print("\n🎉 ¡Código subido correctamente!")


if __name__ == "__main__":
    main()