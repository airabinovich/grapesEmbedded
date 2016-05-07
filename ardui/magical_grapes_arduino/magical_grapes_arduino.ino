#include <Wire.h>
#define HUM 1
#define TEMP 0
const int sensorPinTEMP = 0;
const int sensorPinHUM = 1;
const float divToVolts = 5./1024;
int tempC = 0;
int hum = 0;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  Wire.begin(8);                // join i2c bus with address #8
  Wire.onRequest(requestEvent); // register event
}

void loop() {

  // HUMIDITY  
  hum = (analogRead(sensorPinHUM) / 10.24);

  // TEMPERATURE
  float voltage = analogRead(sensorPinTEMP) * divToVolts;
  
  tempC = (voltage /*- 0.5*/) * 100;

  // PRINT SERIAL
  Serial.print("[SERIAL] Temperature is: ");
  Serial.println(tempC);
  //send humidity by serial
  Serial.print("[SERIAL] Humidity is: ");
  Serial.println(hum);
  
  delay(1000);
}

// function that executes whenever data is requested by master
// this function is registered as an event, see setup()
void requestEvent() {
  
  // SENDING BY SERIAL
  Serial.print("[I2C] Sending data. Temperature: ");
  Serial.print(tempC);
  Serial.print(" Humidity: ");
  Serial.println(hum);

  // SENDING BY I2C
  // respond with message of 6 bytes
  Wire.write(TEMP);
  Wire.write(tempC);
  Wire.write(HUM);
  Wire.write(hum);
}
