const int sensorPinTEMP = 0;
const int sensorPinHUM = 1;
const float divToVolts = 5./1024;

#define nextData "n"
#define BUFFSIZE 512

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
}

void loop() {
  
  int tempC;
  int hum;
  char data[BUFFSIZE];
  // HUMIDITY  
  hum = (analogRead(sensorPinHUM) / 10.24);

  // TEMPERATURE
  float voltage = analogRead(sensorPinTEMP) * divToVolts;
  
  tempC = (voltage /*- 0.5*/) * 100;

  // SENDING BY SERIAL
  sprintf(data, "TEMP:%d,HUM:%d", tempC, hum);
  Serial.println(data);
  delay(800);
}
