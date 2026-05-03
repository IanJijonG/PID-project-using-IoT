#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/atomic.h>
#include <stdint.h>
#include <math.h>

// Pines
#define IN1 19 
#define IN2 18
#define PWM_PIN 25
#define ENCODER_A 26
#define ENCODER_B 27

// Alias para el PWM
#define PWM_NODE DT_ALIAS(pwm_led0)
static const struct pwm_dt_spec pwm_led = PWM_DT_SPEC_GET(PWM_NODE);

// Variables
atomic_t theta = ATOMIC_INIT(0);
int32_t sp = 180;

float pv = 0.0;
float cv = 0.0, cv1 = 0.0;
float error = 0.0, error1 = 0.0, error2 = 0.0;

float Kp = 20.0;
float Ki = 30.0;
float Kd = 0.0;

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
K_THREAD_STACK_DEFINE(stack_led2, STACK_SIZE);

// Threads
struct k_thread pid_thread;
struct k_thread COMjson_thread;
struct k_thread thread_led2;

//Tiempo de muestreo
#define Tm_ms 5
#define Tm (Tm_ms / 1000.0f) //Segundos

// 🔵 Prioridad 1 → PID
void PID_thread(void *a, void *b, void *c)
{
    int64_t next = k_uptime_get();

    while(1){

        //TM
        next += Tm_ms;

        // Planta
        int32_t theta_cnt = atomic_get(&theta);
        pv = theta_cnt * (360.0f / 2483.0f);
        error = sp - pv;

        // PID
        cv = cv1 + (Kp + Kd / Tm) * error + (-Kp + Ki * Tm - 2.0f * Kd / Tm) * error1 + (Kd / Tm) * error2;
        
        // Saturación
        float cvsat = cv;
        if (cvsat > 500.0f)  cvsat = 500.0f;
        if (cvsat < -500.0f) cvsat = -500.0f;

       //Anti-windup 
        if ((cv > 500.0f && error > 0) || (cv < -500.0f && error < 0)) {
            cv = cv1;      //  congela 
        }
        else {
            cv = cvsat;   //  aplica saturación
        }
        
        // Actualizar variables
        cv1 = cv;
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

        // Banda muerta en error — si está cerca del setpoint, para el motor
        if (fabsf(error) < 1.0f) {  // 1 grado de tolerancia
            pwm_set_dt(&pwm_led, period, 0);
            gpio_pin_set(gpio_dev, IN1, 0);
            gpio_pin_set(gpio_dev, IN2, 0);
            cv = 0;
            cv1 = 0;
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

        int64_t now = k_uptime_get();
        int64_t wait = next - now;

        if (wait > 0) {
            k_sleep(K_MSEC(wait));
        }
    }
}

// ================= ENCODER =================
static struct gpio_callback cb_encoderA;
static struct gpio_callback cb_encoderB;

// Equivalente a interrupcion1() de Arduino
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

// Equivalente a interrupcion2() de Arduino
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

// ================= MAIN =================
int main(void)
{
    /*
    // Al inicio del main(), antes de crear hilos
    if (!pwm_is_ready_dt(&pwm_led)) {
        printk("Error: PWM no listo\n");
        return -ENODEV;
    }
    */
    
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

    // Debug
    while(1){
    k_sleep(K_MSEC(500));
    printk("SP: %d CV: %.2f PV: %.2f\n", sp, (double)cv, (double)pv);
    }
    return 0;
}

