from arduino.app_utils import App
import time
import arduino.app_utils as aput
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.dbstorage_sqlstore import SQLStore
import datetime
import csv
import io
import subprocess
import os


PIDVars = {"kp": 0.0, "ki": 0.0, "kd": 0.00}
ModeDict = {'start': 1, 'reset': 0, 'stop': 2}
pv = 0

ui = WebUI()
db = SQLStore("hmi_data.db")

APP_NAME = "user:mce_g26_ian"
SKETCH_FILE = "/app/sketch/sketch.ino"
RESTART_SCRIPT = "/app/restart.sh"

def upload_code(command, data):
    code = data.get("code", "").strip()

    if not code:
        ui.send_message("upload_result", {"ok": False, "msg": "❌ Código vacío"})
        return

    try:
        ui.send_message("upload_result", {"ok": None, "msg": "⏳ Guardando sketch..."})
        with open(SKETCH_FILE, "w") as f:
            f.write(code)
        print(f"[CLI] Sketch guardado en: {SKETCH_FILE}")

        ui.send_message("upload_result", {"ok": None, "msg": "⏳ Compilando y subiendo al MCU..."})

        # nsenter -t 1 ejecuta el comando en el namespace del host (PID 1)
        subprocess.Popen(
            [
                "nsenter", "-t", "1",
                "-m", "-u", "-i", "-n", "-p",
                "--",
                "bash", "/home/arduino/ArduinoApps/mce_g26_ian/restart.sh"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        ui.send_message("upload_result", {
            "ok": True,
            "msg": "✅ Sketch guardado — compilando en segundo plano (~20s)"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        ui.send_message("upload_result", {"ok": False, "msg": f"❌ Error: {str(e)}"})
ui.on_message('code', upload_code)
# Crear tabla si no existe
db.create_table("pv_data", {
    "id": "INTEGER PRIMARY KEY",
    "timestamp": "INTEGER",
    "value": "REAL"
})

def on_get_samples(resource, start, aggr_window):
    result = db.read("pv_data")
    if start and int(start) > 0:
        result = [r for r in result if r["timestamp"] >= int(start)]
    result = result[-100:]
    return [{"ts": r["timestamp"], "value": r["value"]} for r in result]

def get_pv(new_pv):
    global pv
    print("NEW PV:", new_pv, type(new_pv))
    pv = int(new_pv) if new_pv is not None else 0

def meet_web_data(command, data):
    if data['cmd'] == "control_mode":
        print("mode:", data["mode"])
        aput.Bridge.notify("set_control_mode", data["mode"])
    elif data['cmd'] == 'setpoint':
        print("sp:", data['value'])
        aput.Bridge.notify("set_setpoint", str(data["value"]))
    elif data['cmd'] == 'pid':
        PIDVars['kp'] = float(data['kp'])
        PIDVars['ki'] = float(data['ki'])
        PIDVars['kd'] = float(data['kd'])
        aput.Bridge.notify("set_PID_vals", [
            int(PIDVars["kp"] * 10000),
            int(PIDVars["ki"] * 10000),
            int(PIDVars["kd"] * 10000)
        ])
    elif data['cmd'] == "manual":
        action = data['action']
        if action in ModeDict:
            print("jog:", action, "→", ModeDict[action])
            aput.Bridge.notify("set_jog", str(ModeDict[action]))

def download_csv():
    try:
        result = db.read("pv_data")
        lines = ["timestamp,value"]
        for r in result:
            ts = datetime.datetime.fromtimestamp(r["timestamp"] / 1000).isoformat()
            lines.append(f"{ts},{r['value']}")
        return "\n".join(lines)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"error,{repr(e)}"

pv = aput.Bridge.provide("get_pv", get_pv)
ui.on_message('command', meet_web_data)
ui.expose_api("GET", "/get_samples/{resource}/{start}/{aggr_window}", on_get_samples)
ui.expose_api("GET", "/download", download_csv)

def get_events():
    global pv
    try:
        ts = int(datetime.datetime.now().timestamp() * 1000)
        if pv is None:
            pv = 0
        result = db.store("pv_data", {"timestamp": ts, "value": pv})
        print(f"[STORE] ts={ts} pv={pv} result={result}")  # ← debug
        ui.send_message('data', {"value": pv, "ts": ts})
    except Exception as e:
        print("ERROR get_events:", repr(e))
    time.sleep(0.1)

App.run(user_loop=get_events)