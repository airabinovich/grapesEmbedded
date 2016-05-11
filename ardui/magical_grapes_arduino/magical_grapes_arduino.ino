const int sensorPinTEMP = 0;
const int sensorPinHUM = 1;
const float divToVolts = 5./1024;

#define nextData 'n'
#define BUFFSIZE 512

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  pinMode(13,OUTPUT);
}

void loop() {

  int tempC;
  int hum;
  char data[BUFFSIZE];
  
  while(Serial.available()){

    // HUMIDITY  
    hum = (analogRead(sensorPinHUM) / 10.24);
  
    // TEMPERATURE
    float voltage = analogRead(sensorPinTEMP) * divToVolts;
    
    tempC = (voltage /*- 0.5*/) * 100;

  // SENDING BY SERIAL
    if(Serial.read() == nextData){
      digitalWrite(13,HIGH);
      sprintf(data, "TEMP:%d,HUM:%d", tempC, hum);
      delay(750);
      Serial.println(data);
    }
    else{
      delay(700);
    }
    digitalWrite(13,LOW);
  }  
}
