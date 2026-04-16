import subprocess
import sys
import os

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

def compile(FQBN,PROYECTO):
    if not run_command(
        ["arduino-cli", "compile", "--fqbn", FQBN, PROYECTO],
    ):
        sys.exit(1)


def Upload(FQBN,PROYECTO,port):
    if not run_command(
        ["arduino-cli", "upload", "-p", port, "--fqbn", FQBN, PROYECTO],
    ):
        sys.exit(1)

def CreateIno(code):
    os.makedirs("Project", exist_ok=True)
    ruta_archivo = os.path.join("Project", f"{"Project"}.ino")

    
    with open(ruta_archivo, "w") as f:
     f.write(code)
