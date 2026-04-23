from flask import Flask, render_template, Response
from flask_socketio import SocketIO
import threading
import time as t
import subprocess
import DBConnection as DBConn
import queue
import SerialManager as serialM
import CLIworker as cw
import io
import csv
import datetime


app = Flask(__name__)
socketio = SocketIO(app)
JsonVar = {"kp":1.0, "ki":0.1, "kd": 0.05,"sp":0,"mode":False,"button":2}
serial_lock = threading.Lock()

arduinoOriginalINO = "Sketches"

currentMode = 0

temporalList = []

last_serial_time = 0
uploadingFlag = 0
intervalSer = 0 

ser = None

threads_started = False

QUEUE_MAX = 3000
DB_BATCH_SIZE = 100
db_queue = queue.Queue(QUEUE_MAX)
frontend_queue = queue.Queue(QUEUE_MAX)


fqbn = "arduino:avr:uno"
PROYECTO = "ArduinoCodes"


@app.route("/")
def Rederizer():
    """
    Ruta principal de la aplicación.

    Descripción:
        Maneja las solicitudes a la URL raíz ("/") y renderiza
        la plantilla 'HMIv2.html'.

    Variables:
        nombre (str): Cadena que se envía a la plantilla HTML.

    Retorna:
        Response: Página HTML renderizada con la variable 'nombre'.
    """

    nombre = "HMI"
    return render_template("HMIv2.html",nombre=nombre)

@socketio.on("connect")
def handle_connect():
    """
    Evento de conexión de SocketIO.

    Descripción:
        Se ejecuta automáticamente cuando un cliente se conecta
        al servidor mediante SocketIO.

    Funcionalidad:
        - Inicia tareas en segundo plano llamando a
          'start_background_tasks()'.
        - Muestra en consola un mensaje de conexión.

    Retorna:
        None
    """

    start_background_tasks()
    print("Cliente conectado")

@app.route('/export_csv')
def export_csv():
    """
    Ruta para exportar datos en formato CSV.

    Descripción:
        Obtiene datos desde la base de datos y genera un archivo CSV
        dinámico que se descarga automáticamente en el navegador.

    Proceso:
        - Llama a 'DBConn.get_data()' para obtener los registros.
        - Crea un buffer en memoria usando StringIO.
        - Escribe los encabezados del CSV: id, var, timestamp.
        - Recorre los datos y los escribe fila por fila.
        - Reinicia el cursor del buffer con seek(0).

    Retorna:
        Response: Archivo CSV generado en memoria con cabeceras HTTP
        que fuerzan su descarga.

    Headers:
        Content-Disposition:
            Define el nombre del archivo con formato:
            mediciones_YYYYMMDD_HHMMSS.csv

    MIME Type:
        text/csv

    Notas:
        - No se guarda archivo en disco, todo se maneja en memoria.
        - Requiere que 'DBConn.get_data()' retorne una lista de diccionarios
          con las claves: 'id', 'var', 'timestamp'.
    """

    data = DBConn.get_data()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['id','var','timestamp'])

    for i in data:
        writer.writerow([i["id"], i["var"], i["timestamp"]])
    
    output.seek(0)

    return Response(
        output,
        mimetype='text/csv',
        headers={
            "Content-Disposition":
            f"attachment; filename=mediciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )



def start_background_tasks():
    """
    Inicializa tareas en segundo plano para el sistema.

    Descripción:
        Controla la ejecución única de varios procesos en background
        necesarios para el funcionamiento de la aplicación, como
        comunicación serial, envío de datos al frontend y almacenamiento.

    Variables globales:
        threads_started (bool): Indica si los hilos ya fueron iniciados.
        ser: Objeto de conexión serial.
        fqbn: Identificador de la placa (Fully Qualified Board Name).
        uploadingFlag (int): Bandera que evita múltiples cargas de código.

    Proceso:
        - Verifica si los hilos ya fueron iniciados.
        - Si no se ha cargado el código, ejecuta 'Initial_code_charger()'.
        - Establece conexión serial mediante 'serialM.connectionSerial()'.
        - Lanza múltiples tareas en segundo plano con SocketIO:
            * serial_worker: Lectura de datos desde el puerto serial.
            * send_data_Fronted: Envío de datos al cliente.
            * Db_worker: Manejo de base de datos.
            * WatchDog: Supervisión del sistema.

    Retorna:
        bool: True si los hilos ya estaban iniciados.
    """
    global threads_started, ser, fqbn, uploadingFlag

    if threads_started:
        return True

    if uploadingFlag == 0:
        upload_code = Initial_code_charger()
        uploadingFlag = 1


    if upload_code:
        t.sleep(1)
        ser,fqbn = serialM.connectionSerial()
        socketio.start_background_task(serial_worker)
        socketio.start_background_task(send_data_Fronted)
        socketio.start_background_task(Db_worker)
        socketio.start_background_task(WatchDog)

    threads_started = True

@socketio.on("disconnect")
def handle_disconnect():
    """
    Evento de desconexión de cliente SocketIO.

    Descripción:
        Se ejecuta automáticamente cuando un cliente se desconecta
        del servidor. Se encarga de cerrar la conexión serial activa
        de forma segura.

    Variables globales:
        ser: Objeto de conexión serial.

    Proceso:
        - Verifica si la conexión serial existe y está abierta.
        - Cierra la conexión para liberar recursos.

    Manejo de errores:
        - Captura cualquier excepción para evitar que el servidor falle.

    Retorna:
        None
    """
    global ser

    try:
        if ser and ser.is_open:
            ser.close()
    except:
        pass

@socketio.on("command")
def handle_command(data):
    """
    Maneja los comandos recibidos desde el cliente vía SocketIO.

    Descripción:
        Recibe un diccionario con información del comando enviado
        desde el frontend y lo redirige a la función 'command_filter'
        según el tipo de comando.

    Parámetros:
        data (dict): Contiene los datos del comando. Puede incluir:
            - cmd (str): Nombre del comando.
            - value (str/float): Valor asociado (ej. setpoint).
            - action (str): Acción a ejecutar (start, stop, etc.).
            - code (str): Código fuente para cargar.
            - kp, ki, kd (float): Parámetros PID.

    Proceso:
        - Extrae el comando principal ('cmd').
        - Determina qué tipo de acción ejecutar.
        - Llama a 'command_filter' con los parámetros adecuados.

    Retorna:
        None
    """
    dataName = data.get("cmd")
    print(f"Comando recibido: {dataName}")

    if dataName == "pid":
        command_filter(dataName,"-",data)
    elif dataName == "setpoint":
        command_filter(dataName,data.get("value"),data)
    elif dataName == "Code":
        command_filter(dataName,data.get("code"),data)
    else:
        command_filter(dataName,data.get("action"),data)
    

def run_commandCLI(cmd):
    """
    Ejecuta un comando en la línea de comandos del sistema.

    Descripción:
        Lanza un proceso externo usando subprocess y captura
        tanto la salida estándar como los errores.

    Parámetros:
        cmd (list o str): Comando a ejecutar en la terminal.

    Proceso:
        - Ejecuta el comando con subprocess.run().
        - Captura stdout y stderr.
        - Verifica el código de retorno.

    Retorna:
        bool:
            - False si ocurre un error (returncode != 0).
            - None si la ejecución es exitosa (no se define retorno explícito).

    Manejo de errores:
        - Imprime en consola el error y la salida generada.
    """
    
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

def send_data_Fronted():
    """
    Envía datos al frontend en tiempo real mediante SocketIO.

    Descripción:
        Lee datos desde una cola (frontend_queue), los agrupa
        en un buffer y los envía periódicamente al cliente.

    Variables globales:
        ser: Conexión serial (no utilizada directamente aquí).
        intervalSer: Intervalo de muestreo serial.

    Proceso:
        - Intenta obtener datos de la cola con timeout.
        - Almacena los datos en un buffer temporal.
        - Cada 0.1 segundos envía el buffer al frontend.
        - Limpia el buffer después de enviar.

    Evento emitido:
        "data":
            {
                "positions": [valores]
            }

    Retorna:
        None
    """
    global ser, intervalSer
    buffer = []
    last_emit = t.time()

    while True:

        try:
            data = frontend_queue.get(timeout=0.1)
            buffer.append(data)
        except queue.Empty:
            pass

        if t.time() - last_emit >= 0.1:
            if buffer:
                socketio.emit("data", {
                    "positions": buffer
                })
                buffer = []
            last_emit = t.time()

        socketio.sleep(0.01)

def serial_worker():
    """
    Lee datos desde el puerto serial y los distribuye en colas.

    Descripción:
        Ejecuta un bucle infinito que obtiene datos desde el puerto
        serial de forma segura (usando un lock) y los envía a colas
        para su procesamiento en base de datos y frontend.

    Variables globales:
        ser: Objeto de conexión serial.
        intervalSer: Intervalo de lectura actualizado desde el dispositivo.

    Proceso:
        - Accede al puerto serial usando 'serial_lock'.
        - Lee datos mediante 'serialM.read_from_serial()'.
        - Verifica que el dato no sea None.
        - Convierte el dato a tipo float.
        - Inserta el valor en:
            * db_queue (si no está llena)
            * frontend_queue (si no está llena)

    Manejo de errores:
        - Si la conversión falla, muestra "Dato inválido".

    Retorna:
        None
    """
    global ser, intervalSer

    while True:
        with serial_lock:
            position, intervalSer = serialM.read_from_serial(ser)

        if position is not None:
            try:
                position = float(position)

                # Cola para DB
                if not db_queue.full():
                    db_queue.put(position)

                # Cola para frontend
                if not frontend_queue.full():
                    frontend_queue.put(position)

            except:
                print("Dato inválido:", position)

        socketio.sleep(0.01)

    
def reconnect_serial():
    """
    Intenta restablecer la conexión serial en caso de fallo.

    Descripción:
        Cierra la conexión serial actual (si existe) y trata de
        reconectarse al dispositivo. Utiliza un lock para evitar
        conflictos con otros hilos que acceden al puerto.

    Variables globales:
        ser: Objeto de conexión serial.

    Proceso:
        - Adquiere el lock de acceso serial.
        - Cierra la conexión actual si está abierta.
        - Intenta reconectar usando 'serialM.connectionSerial()'.
        - Verifica si la nueva conexión está activa.

    Retorna:
        bool:
            - True si la reconexión fue exitosa.
            - False si falló la reconexión o ocurrió un error.

    Manejo de errores:
        - Captura excepciones generales y muestra el error en consola.
    """
    global ser

    try:
        with serial_lock:
            if ser:
                try:
                    ser.close()
                except:
                    pass

            print("Reintentando conexión serial...")

            ser = serialM.connectionSerial()

            if ser and ser.is_open:
                print("Serial reconectado correctamente")
                return True
            else:
                print("Fallo al reconectar serial")
                return False

    except Exception as e:
        print("Error en reconexión serial:", e)
        return False

def WatchDog():
    """
    Supervisa el estado de la comunicación serial (Watchdog).

    Descripción:
        Monitorea continuamente el tiempo entre lecturas del puerto
        serial (intervalSer). Si el sistema deja de responder dentro
        de un tiempo límite, intenta reconectar automáticamente.

    Variables globales:
        intervalSer (float): Tiempo transcurrido desde la última
        lectura válida del puerto serial.

    Constantes:
        TIMEOUT (float): Tiempo máximo permitido sin respuesta (segundos).

    Proceso:
        - Espera periódicamente (cada 0.5 segundos).
        - Verifica si 'intervalSer' tiene valor válido.
        - Si el intervalo supera el TIMEOUT:
            * Muestra mensaje de error.
            * Llama a 'reconnect_serial()'.
            * Reinicia 'intervalSer' a None.

    Funcionalidad:
        Actúa como un mecanismo de seguridad para evitar bloqueos
        en la comunicación con el dispositivo serial.

    Retorna:
        None
    """
    global intervalSer

    TIMEOUT = 2.0

    while True:
        socketio.sleep(0.5)

        if intervalSer is None:
            continue


        if intervalSer > TIMEOUT:
            print("Watchdog: sistema sin respuesta, reconectando...")
            reconnect_serial()
            intervalSer = None

def command_filter(command,action,data):
    """
    Filtra y ejecuta comandos según su tipo.

    Descripción:
        Procesa distintos comandos del sistema (manual, PID, setpoint,
        modo de control, carga de código) y actualiza variables globales
        o envía información al microcontrolador.

    Parámetros:
        command (str): Tipo de comando recibido.
        action (str): Acción o valor asociado al comando.
        data (dict): Diccionario con datos adicionales.

    Variables globales:
        setpointVar (float): Valor actual del setpoint.
        currentMode (str): Modo de control actual.
        fqbn (str): Identificador de la placa Arduino.

    Comandos soportados:
        - "manual":
            Control de botones (start, stop, reset).
        - "pid":
            Actualiza parámetros kp, ki, kd.
        - "setpoint":
            Define el valor del setpoint.
        - "control_mode":
            Cambia entre modos (velocity u otro).
        - "Code":
            Compila y sube código al dispositivo.

    Proceso:
        - Evalúa el tipo de comando.
        - Actualiza el diccionario 'JsonVar'.
        - Llama a 'Update_json_arduino()' para enviar datos.
        - En el caso de "Code", compila y carga el programa.

    Retorna:
        None
    """
    global setpointVar, currentMode, fqbn

    if command == "manual" and action != "-":
        print("Modo manual activado")

        if action == "stop":
            print("stop")
            JsonVar["button"] = 2

            Update_json_arduino()

        elif action == "start":
            JsonVar["button"] = 1
            print("start")

            Update_json_arduino()

        elif action == "reset":
            print("reset")
            JsonVar["button"] = 0
            Update_json_arduino()

    elif command == "pid" and action == "-":
        JsonVar["kp"] = data.get("kp")
        JsonVar["ki"] = data.get("ki")
        JsonVar["kd"] = data.get("kd")

        Update_json_arduino()

    elif command == "setpoint":
        setpointVar = float(action)
        print( setpointVar)
        JsonVar["sp"] = setpointVar

        Update_json_arduino()

    elif command == "control_mode":
        currentMode= data.get("mode")
        
        if currentMode == "velocity":
            JsonVar["mode"] = True
        else:
            JsonVar["mode"] = False
        print(currentMode)


        Update_json_arduino()
    
    elif command == "Code":
        code = data.get("code")
        port = serialM.detectar_puerto()

        cw.compile(fqbn,code)
        socketio.sleep(1)
        cw.Upload(fqbn,code,port)

def Initial_code_charger():
    global arduinoOriginalINO

    try:
        port, FQBN = serialM.detectar_puerto()

        cw.compile(fqbn,arduinoOriginalINO)
        cw.Upload(FQBN,arduinoOriginalINO,port)

        return True
    
    except:
        return False
    

def Update_json_arduino():
    """
    Envía un JSON al dispositivo a través del puerto serial.

    Descripción:
        Verifica que todas las variables del diccionario 'JsonVar'
        tengan valores válidos antes de enviarlas al microcontrolador
        mediante comunicación serial.

    Variables globales:
        JsonVar (dict): Diccionario con los parámetros a enviar.
        ser: Objeto de conexión serial.

    Proceso:
        - Imprime el contenido actual de 'JsonVar'.
        - Verifica que ningún valor sea None.
        - Si todos los valores son válidos:
            * Adquiere el lock del puerto serial.
            * Envía el JSON mediante 'serialM.writeJsonSerial()'.
        - Si hay valores inválidos:
            * Muestra un mensaje de advertencia.

    Manejo de errores:
        - No lanza excepciones explícitas, solo validación previa.

    Retorna:
        None
    """
    global JsonVar, ser

    print(JsonVar)

    if any(v is None for v in JsonVar.values()):
        print("Agrega valores válidos")
    else:
        with serial_lock:
            serialM.writeJsonSerial(ser, JsonVar)

def Db_worker():
    """
    Procesa y guarda datos en la base de datos en lotes.

    Descripción:
        Ejecuta un bucle continuo que toma datos desde una cola
        (db_queue) y los guarda en la base de datos en bloques
        (batch) para mejorar el rendimiento.

    Dependencias:
        - DBConn.init_db(): Inicializa la base de datos.
        - DBConn.save_position(): Guarda un lote de datos.

    Proceso:
        - Inicializa la base de datos al iniciar.
        - Espera datos en 'db_queue'.
        - Agrupa datos en una lista (lote) hasta alcanzar:
            * Tamaño máximo (DB_BATCH_SIZE), o
            * Que la cola esté vacía.
        - Guarda el lote en la base de datos.
        - Marca cada elemento como procesado con 'task_done()'.

    Variables externas:
        db_queue: Cola compartida de datos.
        DB_BATCH_SIZE (int): Tamaño máximo del lote.

    Manejo de errores:
        - Ignora excepciones de cola vacía y continúa el ciclo.

    Retorna:
        None
    """
    DBConn.init_db()

    while True:
        try:
            item = db_queue.get(timeout=1)
        except queue.Empty:
            continue

        lote = [item]

        while not db_queue.empty() and len(lote) < DB_BATCH_SIZE:
            try:
                lote.append(db_queue.get_nowait())
            except queue.Empty:
                break

        DBConn.save_position(lote)

        for _ in lote:
            db_queue.task_done()


if __name__ == "__main__":

    socketio.run(app, debug=True, use_reloader=False)

