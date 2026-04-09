//Inicialización de Variables
volatile int theta = 0;
volatile int contador= 0;
int sp= 360;
#define IN1 32 //Pines del puente H
#define IN2 33 //Pines del puente H
float pv; 

// Parámetros PWM
# define pwmPIN 25
const int frecuencia=15000;
const int resolucion=12;

// Variables del PID
float cv;      // Control variable (Ley de Control)
float cv1;         // Valor anterior de cv
float error;       // Error actual
float error1;      // Error anterior
float error2;      // Error dos etapas atrás

// Parámetros del PID
float Kp = 1;
float Ki = 0;
float Kd = 0;
float Tm = 0.01; // Tiempo de muestreo

#define EncoderA 26
#define EncoderB 27

hw_timer_t *timer = NULL;

volatile bool tiempo_muestreo = false;

void IRAM_ATTR timerInterrupcion() {
 tiempo_muestreo = true;
}

void IRAM_ATTR interrupcion1(){
  if (digitalRead(EncoderA) != digitalRead(EncoderB)){
     theta++;
  }
  else{
    theta--;
  }
}

void IRAM_ATTR interrupcion2(){
  if (digitalRead(EncoderA) == digitalRead(EncoderB)){
    theta++;
  }
  else{
    theta--;
  }
}

//Tiempo de muestreo
unsigned long lastTime = 0;
const unsigned long Ts_us = 10000; // 10 ms

void setup() {
  Serial.begin(115200);
  ledcAttach(pwmPIN, frecuencia, resolucion);

  pinMode(EncoderA, INPUT_PULLUP);
  pinMode(EncoderB, INPUT_PULLUP);

  pinMode(IN1, OUTPUT); // Configurar IN1 como salida
  pinMode(IN2, OUTPUT); // Configurar IN2 como salida
  pinMode(pwmPIN, OUTPUT);

  attachInterrupt(digitalPinToInterrupt(EncoderB),interrupcion1,CHANGE); //Flanco de subida 
  attachInterrupt(digitalPinToInterrupt(EncoderA),interrupcion2,CHANGE); //Flanco de subida 

  timer = timerBegin(1000000); // 1 MHz -> 1 tick = 1 us
  timerAttachInterrupt(timer, &timerInterrupcion);
  timerAlarm(timer, 10000, true, 0); // 10 ms
  

}

void loop() {
if (tiempo_muestreo){
  tiempo_muestreo = false;

  pv = theta * (360.0 / 2483.0); //ángulo del eje principal CAMBIAR 1121 POR PPR

  error = sp - pv;

  // --- Ecuación de diferencias del PID ---
  cv = cv1 + (Kp + Kd / Tm) * error + (-Kp + Ki * Tm - 2 * Kd / Tm) * error1 + (Kd / Tm) * error2;
  cv1 = cv; // Guardar valor actual de cv
  error2 = error1; // Actualizar errores
  error1 = error;

// --- Saturar la salida del PID ---
  if (cv > 500.0) { 
    cv = 500.0;
  }
  if (cv < -500.0) { 
    cv = -500.0;
  }

  if (cv >= 0) {
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
    ledcWrite(pwmPIN, (cv * 4095.0 / 500.0));
    } 
    else if (cv < 0) {
      digitalWrite(IN1, LOW);
      digitalWrite(IN2, HIGH);
      ledcWrite(pwmPIN, (abs(cv) * 4095.0 / 500.0));
    } 

  Serial.print("SP: ");
  Serial.print(pv);
  Serial.print(" CV: ");
  Serial.print(cv);
  Serial.print(" PPR: ");
  Serial.println(theta);
  
}
}


