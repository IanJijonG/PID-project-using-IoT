#include <ArduinoJson.h>

//Inicialización de Variables

volatile int theta = 0; //Variable volatil de la interrupción del sensor
float setpoint=0;         //valor del SetPoint
int caso;               //variable de los casos para modificar ganancias
bool mode;              //Bandera de modo (velocidad/posición) 
int button;             //Botones de restart, start y stop {0, 1 y 2}

#define IN1 33          //Pines del puente H
#define IN2 32          //Pines del puente H
#define pwmPIN 25       //Pin del PWM del Puente H
#define EncoderA 26     //Pines del sensor Hall
#define EncoderB 27     //Pines del sensor Hall

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
float pv;        //Valor del sensor en grados o en RPM

//-----Timer por Hardware-----
hw_timer_t *timer = NULL;

volatile bool tiempo_muestreo = false;

void IRAM_ATTR timerInterrupcion() { //Flag del timer para respetar el Tm
 tiempo_muestreo = true;
}

//----- Interrupciones del sensor------
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

void setup() {
  Serial.begin(115200);

  pinMode(EncoderA, INPUT_PULLUP);  //Pullup en el sensor para evitar flancos altos falsos (ruido)
  pinMode(EncoderB, INPUT_PULLUP);

  pinMode(IN1, OUTPUT); 
  pinMode(IN2, OUTPUT); 
  pinMode(pwmPIN, OUTPUT);

  attachInterrupt(digitalPinToInterrupt(EncoderB),interrupcion1,CHANGE); //Cada que detecta un cambio de flanco
  attachInterrupt(digitalPinToInterrupt(EncoderA),interrupcion2,CHANGE); //Cada que detecta un cambio de flanco

  timer = timerBegin(1000000); // 1 MHz -> 1 tick = 1 us
  timerAttachInterrupt(timer, &timerInterrupcion);
  timerAlarm(timer, 10000, true, 0); // 10 ms
  
}

void loop() {
  if (Serial.available()) {
  String input = Serial.readStringUntil('\n');

  if (input.startsWith("{")) {
    deserializarJSON(input.c_str());
  } else {
    // lógica normal
  }
}

  if (Serial.available() > 0){

  String input = Serial.readStringUntil('\n');
  caso = input.toFloat();

  Serial.print("Caso seleccionado: ");
  Serial.println(caso);

  if(input.startsWith("velocidad")){
    
    mode = true;

  }
  if(input.startsWith("posicion")){
    
    mode = false;

  }

  if(input.startsWith("sp")){
    
    setpoint = input.substring(3).toInt();

    Serial.print("Nuevo SP: ");
    Serial.println(setpoint);

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
     Kp = 7.7;
      Ki = 0.1;
      Kd = 1;
      resetPID();
    break;

    case 6:
     Kp = 0;
      Ki = 0;
      Kd = 0;
      setpoint = 0;
      resetPID();

    break;

    case 7:
     Kp = 6;
      Ki = 3;
      Kd = 0.2;
      resetPID();

    break;
  }


if (tiempo_muestreo){
  tiempo_muestreo = false;

  if(mode){
    velocidad();
  }
  else{
    posicion();
  }

  error = setpoint - pv;

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
  } 
  else if (cv < 0) {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
  } 
  if (button != 2){
    cv = 0;
  }

  //Serial.print("SP: ");
  //Serial.print(sp);
  //Serial.print(" CV: ");
  //Serial.print(cv);
  //Serial.print(" PV: ");
  Serial.println(pv);
  //Serial.print(" Ganancias: ");
  //Serial.println(Kp);
  //Serial.print(", ");
  //Serial.println(mode);
  //Serial.print(", ");
  //Serial.println(mode);

  if(mode){
    theta=0;
  } 
}
}

void resetPID(){
  error = 0;
  error1 = 0;
  error2 = 0;

  cv = 0;
  cv1 = 0;
}

void velocidad(){
  pv= theta*2.416; //Conversión de ppr a RPM
}

void posicion(){
  pv = theta * (360.0 / 2483.0); //ángulo del eje principal
}

void deserializarJSON(const char* json) {
    StaticJsonDocument<1024> doc;
    DeserializationError error = deserializeJson(doc, json);
    if (error) {
        Serial.print("Error al parsear JSON: ");
        Serial.println(error.c_str());
        return;
    }

    if (doc.containsKey("kp")) Kp = doc["kp"];
    if (doc.containsKey("ki")) Ki = doc["ki"];
    if (doc.containsKey("kd")) Kd = doc["kd"];

    if (doc.containsKey("sp")) setpoint = doc["sp"];

    if (doc.containsKey("mode")) mode = doc["mode"];
    if (doc.containsKey("button")) button = doc["button"];
}
