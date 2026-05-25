from arduino.app_utils import App
import time
import arduino.app_utils as aput
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.dbstorage_tsstore import TimeSeriesStore
import datetime

PIDVars = {"kp": 0.0, "ki": 0.0, "kd": 0.00}
ModeDict = {'start': 1, 'reset': 0, 'stop': 2}
pv = 0

ui = WebUI()
db = TimeSeriesStore()
print(dir(db))

def on_get_samples(resource, start, aggr_window):
    samples = db.read_samples(measure=resource, start_from=start,
                              aggr_window=aggr_window, aggr_func="mean", limit=100)
    return [{"ts": s[1], "value": s[2]} for s in samples]

def get_pv(new_pv):
    global pv
    print("NEW PV:", new_pv, type(new_pv))
    pv = int(new_pv) if new_pv is not None else 0  # ✅ actualiza la variable global

def meet_web_data(command, data):
    if data['cmd'] == "control_mode":
        print("mode:", data["mode"])
        aput.Bridge.notify("set_control_mode", data["mode"])

    elif data['cmd'] == 'setpoint':
        print("sp:", data['value'])
        aput.Bridge.notify("set_setpoint", str(data["value"]))  # ✅ int

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

pv = aput.Bridge.provide("get_pv", get_pv)
ui.on_message('command', meet_web_data)
ui.expose_api("GET", "/get_samples/{resource}/{start}/{aggr_window}", on_get_samples)

def get_events():
    global pv
    try:
        ts = int(datetime.datetime.now().timestamp() * 1000)
        if pv is None:
            pv = 0
        db.write_sample('pv', pv, ts)
        ui.send_message('data', {"value": pv, "ts": ts})
        
    except Exception as e:
        print("ERROR:", e)
    time.sleep(0.1)

App.run(user_loop=get_events)