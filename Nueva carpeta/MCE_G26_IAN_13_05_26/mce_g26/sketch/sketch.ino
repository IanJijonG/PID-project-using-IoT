#include "Arduino_RouterBridge.h"
#include <zephyr/kernel.h>   // k_thread, k_mutex, k_sleep, atomic_t

// Pines
#define IN1        9
#define IN2        8
#define PWM_PIN    10
#define ENCODER_A  6
#define ENCODER_B  7
#define PIN_SENSOR  4

// Tiempo de muestreo
#define Tm_ms  5
#define Tm     (Tm_ms / 1000.0f)   // segundos

// Variables del encoder (acceso desde ISR → atomic)
atomic_t theta = ATOMIC_INIT(0);

// Mutex para proteger variables compartidas
K_MUTEX_DEFINE(pid_mutex);

// Variables del PID (protegidas por mutex)
float Kp     = 2.0f;
float Ki     = 3.0f;
float Kd     = 0.0f;
float sp     = 30.0f;
int   mode   = 0;    // 0 = Posición, 1 = Velocidad
int   button = 1;    // 0 = Restart, 1 = Start, 2 = Stop

// Variables internas del PID (solo usa PID_thread)
static float pv     = 0.0f;
static float cv     = 0.0f;
static float cv1    = 0.0f;
static float error_pid  = 0.0f;
static float error1     = 0.0f;
static float error2     = 0.0f;

// Stacks y descriptores de hilos Zephyr
#define STACK_SIZE 2048

K_THREAD_STACK_DEFINE(PID_stack,     STACK_SIZE);
K_THREAD_STACK_DEFINE(COMjson_stack, STACK_SIZE);
K_THREAD_STACK_DEFINE(SENSOR_stack,  STACK_SIZE);

struct k_thread pid_thread_data;
struct k_thread comjson_thread_data;
struct k_thread sensor_thread_data;

// ISR del encoder 
void interrupcion1() {
    // Dispara en ENCODER_A
    if (digitalRead(ENCODER_A) != digitalRead(ENCODER_B)) {
        atomic_inc(&theta);
    } else {
        atomic_dec(&theta);
    }
}

void interrupcion2() {
    // Dispara en ENCODER_B
    if (digitalRead(ENCODER_A) == digitalRead(ENCODER_B)) {
        atomic_inc(&theta);
    } else {
        atomic_dec(&theta);
    }
}

void resetPID() {
    cv = cv1 = 0.0f;
    error_pid = error1 = error2 = 0.0f;
}

// ─────────────────────────────────────────────
// Hilo 1 — PID  (mayor prioridad)
// ─────────────────────────────────────────────
void PID_thread(void *a, void *b, void *c) {
    int64_t next = k_uptime_get();

    while (1) {
        next += Tm_ms;

        // Leer parámetros compartidos
        float kp_local, ki_local, kd_local, sp_local;
        int   mode_local, button_local;

        k_mutex_lock(&pid_mutex, K_FOREVER);
        kp_local = Kp;
        ki_local = Ki;
        kd_local = Kd;
        sp_local = sp;
        mode_local = mode;
        button_local = button;
        k_mutex_unlock(&pid_mutex);

        // ── Proceso variable (PV) ──
        int32_t cnt = atomic_get(&theta);

        if (mode_local == 1) {          // Velocidad
            pv = cnt * 2.416f;      // PPR → RPM
        } else {                    // Posición
            pv = cnt * (360.0f / 2483.0f);
        }

        // ── Error ──
        error_pid = sp_local - pv;

        // ── Ecuación de diferencias PID ──
        cv = cv1
           + (kp_local + kd_local / Tm) * error_pid
           + (-kp_local + ki_local * Tm - 2.0f * kd_local / Tm) * error1
           + (kd_local / Tm) * error2;

        // ── Saturación ──
        float cv_sat = cv;
        if (cv_sat >  500.0f) cv_sat =  500.0f;
        if (cv_sat < -500.0f) cv_sat = -500.0f;

        // ── Anti-windup back-calculation ──
        const float k_aw = 0.05f;
        cv1 = cv_sat + k_aw * (cv_sat - cv);
        cv  = cv_sat;

        // ── Actualizar historial ──
        error2 = error1;
        error1 = error_pid;

        // ── Zona muerta del actuador ──
        if (cv > 10.0f) {
            cv = (cv / 500.0f) * (500.0f - 190.0f) + 190.0f;
        } else if (cv < -10.0f) {
            cv = (cv / 500.0f) * (500.0f - 190.0f) - 190.0f;
        }

        // ── PWM (10 kHz via analogWrite — el core del UNO Q lo mapea) ──
        int pwm_val = (int)(fabsf(cv) / 500.0f * 255.0f);

        // ── Lógica de botones ──
        if (button_local == 1) {        // START
            if (mode_local == 0) {      // Posición
                if (fabsf(error_pid) < 1.0f) {
                    // Dentro de banda muerta → detener
                    analogWrite(PWM_PIN, 0);
                    digitalWrite(IN1, LOW);
                    digitalWrite(IN2, LOW);
                    cv = 0.0f;
                } 
                else {
                    analogWrite(PWM_PIN, pwm_val);
                    if (cv > 0) {
                        digitalWrite(IN1, LOW);
                        digitalWrite(IN2, HIGH);
                    } 
                    else {
                        digitalWrite(IN1, HIGH);
                        digitalWrite(IN2, LOW);
                    }
                }
            } 
            else {                // Velocidad
                analogWrite(PWM_PIN, pwm_val);
                if (cv > 0) {
                    digitalWrite(IN1, LOW);
                    digitalWrite(IN2, HIGH);
                } 
                else {
                    digitalWrite(IN1, HIGH);
                    digitalWrite(IN2, LOW);
                }
            }
        }
        else if (button_local == 2) {   // STOP
            analogWrite(PWM_PIN, 0);
            digitalWrite(IN1, LOW);
            digitalWrite(IN2, LOW);
            cv = 0.0f; cv1 = 0.0f;
        }
        else if (button_local == 0) {   // RESTART — avanza hasta sensor
            analogWrite(PWM_PIN, 96);   // ~38% duty (≈50/130 del .ino original)AJUSTAR
            digitalWrite(IN1, HIGH);
            digitalWrite(IN2, LOW);
            resetPID();
        }

        // En modo velocidad, reiniciar contador para no acumular
        if (mode_local == 1) {
            atomic_set(&theta, 0);
        }

        int64_t wait = next - k_uptime_get();
        if (wait > 0) k_sleep(K_MSEC(wait));
    }
}

void SENSOR_thread(void *a, void *b, void *c) {
    /*while (1) {
        if (digitalRead(PIN_SENSOR) == HIGH) {
            // Llegó al punto inicial → detener
            k_mutex_lock(&pid_mutex, K_FOREVER);
            button = 2;  // Stop automático
            k_mutex_unlock(&pid_mutex);
        }
        k_sleep(K_MSEC(10));
    }*/
}

void printFloat(double value, int decimals = 6) {
    if (value < 0) {
        Monitor.print("-");
        value = -value;
    }

    long intPart = (long)value;
    long fracPart = (long)((value - intPart) * pow(10, decimals));

    Monitor.print(intPart);
    Monitor.print(".");

    // zero-padding for fractional part
    long scale = pow(10, decimals - 1);
    while (fracPart < scale && scale > 1) {
        Monitor.print("0");
        scale /= 10;
    }

    Monitor.println(fracPart);
}

// ── Callbacks corregidas — actualizan variables CON mutex ──

void get_PID_vals(std::array<uint32_t, 3> PID) {
    k_mutex_lock(&pid_mutex, K_FOREVER);
    Kp = (float)PID[0] / 10000.0f;
    Ki = (float)PID[1] / 10000.0f;
    Kd = (float)PID[2] / 10000.0f;
    k_mutex_unlock(&pid_mutex);

    printMonitor("kp=", Kp);
    printMonitor("ki=", Ki);
    printMonitor("kd=", Kd);
}

void get_control_mode(String modeStr) {
    k_mutex_lock(&pid_mutex, K_FOREVER);
    mode = (modeStr == "velocity") ? 1 : 0;
    k_mutex_unlock(&pid_mutex);
    Monitor.println(modeStr);
}

void get_setpoint(String setpointStr) {
    int val = setpointStr.toInt();

    k_mutex_lock(&pid_mutex, K_FOREVER);
    sp = (float)val;
    k_mutex_unlock(&pid_mutex);

    char buf[20];
    snprintf(buf, sizeof(buf), "sp=%d", val);
    Monitor.println(buf);
}

void get_jog(String jogMode) {
    int val = jogMode.toInt();

    char buf[24];
    snprintf(buf, sizeof(buf), "jog raw=%s int=%d", jogMode.c_str(), val);
    Monitor.println(buf);

    if (val == 0 || val == 1 || val == 2) {
        k_mutex_lock(&pid_mutex, K_FOREVER);
        button = val;
        k_mutex_unlock(&pid_mutex);
    }
}

float set_pv(float pvtemp){
  return pvtemp;
}

// Reemplaza dtostrf con esta función
void printMonitor(const char* label, float value) {
    // Separa parte entera y decimal manualmente (sin %f)
    int entero  = (int)value;
    int decimal = (int)(fabsf(value - entero) * 100);  // 2 decimales

    char buf[32];
    if (value < 0 && entero == 0) {
        // Caso especial: -0.xx
        snprintf(buf, sizeof(buf), "%s-0.%02d", label, decimal);
    } else {
        snprintf(buf, sizeof(buf), "%s%d.%02d", label, entero, decimal);
    }
    Monitor.println(buf);
}

void setup() {

    Monitor.begin(9600);
  
  // Pines de dirección
    pinMode(IN1,      OUTPUT);
    pinMode(IN2,      OUTPUT);
    pinMode(PWM_PIN,  OUTPUT);

    // Pines encoder con pull-up (filtra ruido eléctrico)
    pinMode(ENCODER_A, INPUT_PULLUP);
    pinMode(ENCODER_B, INPUT_PULLUP);

    // Sensor fin de carrera
    pinMode(PIN_SENSOR, INPUT_PULLUP);

    // Interrupciones del encoder
    attachInterrupt(digitalPinToInterrupt(ENCODER_A), interrupcion2, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENCODER_B), interrupcion1, CHANGE);

    Bridge.begin();
    Bridge.provide("set_control_mode",get_control_mode);
    Bridge.provide("set_setpoint",get_setpoint);
    Bridge.provide("set_PID_vals",get_PID_vals);
    Bridge.provide("set_jog",get_jog);
  
    // ── Crear hilos Zephyr ──
    k_thread_create(
        &pid_thread_data, PID_stack, STACK_SIZE,
        PID_thread, NULL, NULL, NULL,
        1, 0, K_NO_WAIT   // Prioridad 1 (mayor)
    );

    k_thread_create(
        &sensor_thread_data, SENSOR_stack, STACK_SIZE,
        SENSOR_thread, NULL, NULL, NULL,
        2, 0, K_NO_WAIT   // Prioridad 2 (menor)
    );

//

}


void loop() {
    Bridge.notify("get_pv", set_pv(pv));
    printMonitor("cv=", cv);
    printMonitor("pv=", pv);
    
    char buf[16];
    snprintf(buf, sizeof(buf), "btn=%d", button);
    Monitor.println(buf);
  
    //printMonitor("error=", error_pid);
    //printMonitor("pv=", pv);
    k_sleep(K_MSEC(500));
}
  

