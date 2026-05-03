#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/data/json.h>
#include <zephyr/drivers/uart.h>
#include <stdint.h>
#include <math.h>

// Pines
#define IN1 19 
#define IN2 18
#define PWM_PIN 25
#define ENCODER_A 26
#define ENCODER_B 27
#define PIN_SENSOR 4

#define UART_BUF_SIZE 128

// Alias para el PWM
#define PWM_NODE DT_ALIAS(pwm_led0)
static const struct pwm_dt_spec pwm_led = PWM_DT_SPEC_GET(PWM_NODE);

// Variables
atomic_t theta = ATOMIC_INIT(0);
K_MUTEX_DEFINE(pid_mutex);
int32_t sp = 30;

float pv = 0.0;
float cv = 0.0, cv1 = 0.0;
float error = 0.0, error1 = 0.0, error2 = 0.0;

float Kp = 2.0;
float Ki = 3.0;
float Kd = 0.0;

int mode = 0;   // 1: Velocidad, 0: Posición
int button = 0; // 0: Restart, 1: Start, 2: Stop

//Tiempo de muestreo
#define Tm_ms 5
#define Tm (Tm_ms / 1000.0f) //Segundos

// Dispositivos
const struct device *gpio_dev;

// Configuración
#define STACK_SIZE 2048

// Prioridades (menor número = mayor prioridad)
#define PRIORITY0 1
#define PRIORITY1 2
#define PRIORITY2 3

// Stacks
K_THREAD_STACK_DEFINE(PID_stack, STACK_SIZE);
K_THREAD_STACK_DEFINE(COMjson_stack, STACK_SIZE);
K_THREAD_STACK_DEFINE(SENSOR_stack, STACK_SIZE);

// Threads
struct k_thread pid_thread;
struct k_thread comjson_thread;
struct k_thread sensor_thread;

// Json
struct pid_config {
    double kp;
    double ki;
    double kd;
    double sp;
    int mode;
    int button;
};

static const struct json_obj_descr pid_descr[] = {
    JSON_OBJ_DESCR_PRIM(struct pid_config, kp, JSON_TOK_NUMBER),
    JSON_OBJ_DESCR_PRIM(struct pid_config, ki, JSON_TOK_NUMBER),
    JSON_OBJ_DESCR_PRIM(struct pid_config, kd, JSON_TOK_NUMBER),
    JSON_OBJ_DESCR_PRIM(struct pid_config, sp, JSON_TOK_NUMBER),
    JSON_OBJ_DESCR_PRIM(struct pid_config, mode, JSON_TOK_NUMBER),
    JSON_OBJ_DESCR_PRIM(struct pid_config, button, JSON_TOK_NUMBER),
};

// ================= ENCODER =================
static struct gpio_callback cb_encoderA;
static struct gpio_callback cb_encoderB;

// Equivalente a interrupcion1()
void encoder_isrA(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
    int a = gpio_pin_get(dev, ENCODER_A);
    int b = gpio_pin_get(dev, ENCODER_B);

    if (a != b) {
        atomic_inc(&theta);
    } else {
        atomic_dec(&theta);
    }
}

// Equivalente a interrupcion2()
void encoder_isrB(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
    int a = gpio_pin_get(dev, ENCODER_A);
    int b = gpio_pin_get(dev, ENCODER_B);

    if (a == b) {
        atomic_inc(&theta);
    } else {
        atomic_dec(&theta);
    }
}

//Deserialización JSON
void deserializar_json(char *json)
{
    struct pid_config cfg;

    int ret = json_obj_parse(
        json,
        strlen(json),
        pid_descr,
        ARRAY_SIZE(pid_descr),
        &cfg
    );

    if (ret < 0) {
        printk("Error al parsear JSON: %d\n", ret);
        return;
    }

    // 🔒 PROTEGER ESCRITURA
    k_mutex_lock(&pid_mutex, K_FOREVER);

    Kp = cfg.kp;
    Ki = cfg.ki;
    Kd = cfg.kd;
    sp = (int32_t)cfg.sp;
    mode = cfg.mode;
    button = cfg.button;

    k_mutex_unlock(&pid_mutex);
}

// 🔵 Prioridad 1 → PID
void PID_thread(void *a, void *b, void *c)
{
    int64_t next = k_uptime_get();

    while(1){

        //TM
        next += Tm_ms;

         // 🔒 LEER VARIABLES SEGURAS
        float kp, ki, kd;
        int32_t sp_local;
        int mode_local, button_local;

        k_mutex_lock(&pid_mutex, K_FOREVER);

        kp = Kp;
        ki = Ki;
        kd = Kd;
        mode_local = mode;
        button_local = button;
        sp_local = sp;

        k_mutex_unlock(&pid_mutex);

        // Planta
        int32_t theta_cnt = atomic_get(&theta);

        if (mode_local == 1) { // Velocidad
            pv = theta_cnt * 2.416; //Conversión de ppr a RPM}
        }
        else { // Posición
            pv = theta_cnt * (360.0f / 2483.0f);
        }
        
        error = sp_local - pv;

        // PID
        cv = cv1 + (kp + kd / Tm) * error + (-kp + ki * Tm - 2.0f * kd / Tm) * error1 + (kd / Tm) * error2;
        
        // Saturación
        float cv_sat = cv;
        if (cv_sat > 500.0f)  cv_sat = 500.0f;
        if (cv_sat < -500.0f) cv_sat = -500.0f;

        //Anti-windup por back-calculation
        float k_aw = 0.05f; // Ganancia anti-windup (ajustable)
        cv1 = cv_sat + k_aw * (cv_sat - cv);
        cv = cv_sat;

       /* Anti-windup por congelamiento (clamping)
        if ((cv > 500.0f && error > 0) || (cv < -500.0f && error < 0)) {
            cv = cv1;      //  congela 
        }
        else {
            cv = cvsat;   //  aplica saturación
        }*/
        
        // Actualizar variables
        //cv1 = cv;
        error2 = error1;
        error1 = error;

        //Zona muerta         
        if (cv > 10) {
            cv = (cv / 500.0f) * (500 - 190) + 190;
        }       
        else if (cv < -10) {
            cv = (cv / 500.0f) * (500 - 190) - 190;
        }

        //PWM
        uint32_t period = 100000; // 100 µs → 10 kHz (mejor para motor)
        float duty = fabsf(cv) / 500.0f;
        if (duty > 1.0f) duty = 1.0f;
        uint32_t pulse = (uint32_t)(duty * period);

        if (button_local == 1) { // Start
            if(mode_local == 0){
                // Banda muerta en error — si está cerca del setpoint, para el motor
                if (fabsf(error) < 1.0f) {  // 1 grado de tolerancia
                    pwm_set_dt(&pwm_led, period, 0);
                    gpio_pin_set(gpio_dev, IN1, 0);
                    gpio_pin_set(gpio_dev, IN2, 0);
                    cv = 0;
                    //cv1 = 0;
                } 
            }
            //Dirección
            else {
                pwm_set_dt(&pwm_led, period, pulse);

                if (cv > 0) {
                    gpio_pin_set(gpio_dev, IN1, 0);
                    gpio_pin_set(gpio_dev, IN2, 1);
                } 
                else if (cv < 0) {
                    gpio_pin_set(gpio_dev, IN1, 1);
                    gpio_pin_set(gpio_dev, IN2, 0);
                }
            }
        }
        else if (button_local == 2) { // Stop
            pwm_set_dt(&pwm_led, period, 0);
            gpio_pin_set(gpio_dev, IN1, 0);
            gpio_pin_set(gpio_dev, IN2, 0);
            cv = 0;
            cv1 = 0;
        }
        else if (button_local == 0) { // Restart
            uint32_t pulse_restart = (uint32_t)(0.5f * period); // 50% duty
            pwm_set_dt(&pwm_led, period, pulse_restart); 
            gpio_pin_set(gpio_dev, IN1, 1);
            gpio_pin_set(gpio_dev, IN2, 0);
            cv=0;
            cv1=0;
            error1 = 0;
            error2 = 0;
        }

        if (mode_local == 1) { // Velocidad
            theta_cnt = 0; // Reinicia el conteo para evitar overflow
            atomic_set(&theta, theta_cnt);
        }

        int64_t now = k_uptime_get();
        int64_t wait = next - now;

        if (wait > 0) {
            k_sleep(K_MSEC(wait));
        }
    }
}

// 🔵 Prioridad 2 → Comunicación JSON 
void COMjson_thread(void *a, void *b, void *c)
{
    //int64_t next = k_uptime_get();

    const struct device *uart = DEVICE_DT_GET(DT_CHOSEN(zephyr_console));
    static char buffer[UART_BUF_SIZE];  //Guarda el JSON recibido
    int idx = 0;                        //Posición que va leyendo

    while(1){

        uint8_t c;
        if (uart_poll_in(uart, &c) == 0){        //Devuelve 0 si se leyó un byte

            if (c == '\n' || c == '\r'){            //Detectar fin de mensaje
                buffer[idx] = '\0';                 //Termina el string

                if (idx > 0 && buffer[0] == '{') {
                    deserializar_json(buffer);           //Parsea el JSON
                }
                idx = 0;                            //Reinicia índice para próximo mensaje
            }
                            
            else {
                if (idx < UART_BUF_SIZE - 1) {     //Evita overflow
                buffer[idx++] = c;                  //Agrega byte al buffer
                } 
                else { 
                    idx = 0; // overflow 
                }
            }
        }           
    k_sleep(K_MSEC(200));
    }
}

// 🔵 Prioridad 3 → Sensor para RESTART
void SENSOR_thread(void *a, void *b, void *c)
{
    while(1) {
        // Lee el sensor externo
        int sensor = gpio_pin_get(gpio_dev, PIN_SENSOR);

        if (sensor == 1) {  // llegó al punto inicial
            k_mutex_lock(&pid_mutex, K_FOREVER);
            button = 2;  // cambia a Stop automáticamente
            k_mutex_unlock(&pid_mutex);
        }

        k_sleep(K_MSEC(100));  // revisa cada 100ms
    }
}

// ================= MAIN =================
int main(void)
{   
    gpio_dev = DEVICE_DT_GET(DT_NODELABEL(gpio0));

    // Configurar pines
    gpio_pin_configure(gpio_dev, IN1, GPIO_OUTPUT);
    gpio_pin_configure(gpio_dev, IN2, GPIO_OUTPUT);

    gpio_pin_configure(gpio_dev, ENCODER_A, GPIO_INPUT | GPIO_PULL_UP);
    gpio_pin_configure(gpio_dev, ENCODER_B, GPIO_INPUT | GPIO_PULL_UP);

    // Interrupciones encoder
    gpio_pin_interrupt_configure(gpio_dev, ENCODER_A, GPIO_INT_EDGE_BOTH);
    gpio_pin_interrupt_configure(gpio_dev, ENCODER_B, GPIO_INT_EDGE_BOTH);
    gpio_init_callback(&cb_encoderA, encoder_isrA, BIT(ENCODER_A));
    gpio_init_callback(&cb_encoderB, encoder_isrB, BIT(ENCODER_B));
    gpio_add_callback(gpio_dev, &cb_encoderA);
    gpio_add_callback(gpio_dev, &cb_encoderB);

    // Crear hilos
    k_thread_create(&pid_thread, PID_stack, STACK_SIZE,
                    PID_thread, NULL, NULL, NULL,
                    PRIORITY0, 0, K_NO_WAIT);

    k_thread_create(&comjson_thread, COMjson_stack, STACK_SIZE,
                    COMjson_thread, NULL, NULL, NULL,
                    PRIORITY1, 0, K_NO_WAIT);

    k_thread_create(&sensor_thread, SENSOR_stack, STACK_SIZE,
                    SENSOR_thread, NULL, NULL, NULL,
                    PRIORITY2, 0, K_NO_WAIT);

    // Debug
    while(1){
    k_sleep(K_MSEC(500));
    printk("SP: %d CV: %.2f PV: %.2f\n", sp, (double)cv, (double)pv);
    }
    return 0;
}

