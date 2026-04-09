//Inicialización de Variables
volatile int theta = 0;
volatile int contador= 0;
int sp = 0;
int caso;
#define IN1 32 //Pines del puente H
#define IN2 33 //Pines del puente H
float pv; 
float pulsos = 2483.0;

# define pwmPIN 25

// Variables del PID
float cv;      // Control variable (Ley de Control)
float cv1;         // Valor anterior de cv
float error;       // Error actual
float error1;      // Error anterior
float error2;      // Error dos etapas atrás

// Parámetros del PID
float Kp;
float Ki;
float Kd;
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
  //ledcAttach(pwmPIN, frecuencia, resolucion);

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
  if (Serial.available() > 0){

  String input = Serial.readStringUntil('\n');
  caso = input.toFloat();

  Serial.print("Caso seleccionado: ");
  Serial.println(caso);

  if(input.startsWith("sp")){
    
    sp = input.substring(3).toInt();

    Serial.print("Nuevo SP: ");
    Serial.println(sp);

  }

  }


  switch(caso){

    case 1:
      Kp = 500;
     Ki = 0;
     Kd = 0;
     resetPID();
    break;

    case 2:
      Kp = 1000;
      Ki = 0;
      Kd = 0;
      resetPID();
    break;

    case 3:
      Kp = 500;
      Ki = 0;
      Kd = 25;
      resetPID();
    break;

    case 4:
      Kp = 400;
      Ki = 400;
      Kd = 0;
      resetPID();
    break;

    case 5:
     Kp = 6;
      Ki = 3;
      Kd = 0.2;
      resetPID();
    break;

    case 6:
     Kp = 0;
      Ki = 0;
      Kd = 0;
      sp = 0;
      resetPID();

    break;

  }

if (tiempo_muestreo){
  tiempo_muestreo = false;

  pv= theta*2.416; //Conversión de ppr a RPM

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
    analogWrite(pwmPIN, (abs(cv) * 255.0 / 500.0));
    
    } 
    else if (cv < 0) {
      digitalWrite(IN1, LOW);
      digitalWrite(IN2, HIGH);
      analogWrite(pwmPIN, (abs(cv) * 255.0 / 500.0));
      
    } 

  Serial.print("SP: ");
  Serial.print(sp);
  Serial.print(" CV: ");
  Serial.print(cv);
  Serial.print(" PV: ");
  Serial.print(pv);
  Serial.print(" Ganancias: ");
  Serial.print(Kp);
  Serial.print(", ");
  Serial.print(Ki);
  Serial.print(", ");
  Serial.println(Kd);
  
  theta = 0;
}
}

void resetPID(){

  error = 0;
  error1 = 0;
  error2 = 0;

  cv = 0;
  cv1 = 0;

}
