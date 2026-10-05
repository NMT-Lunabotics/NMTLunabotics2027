const unsigned long BAUD_RATE=115200; 

const unsigned long ABC_INTERVAL=1000;
const unsigned long DEF_INTERVAL=5000;
const unsigned long HIJ_INTERVAL=3000;

unsigned long lastABC=0;
unsigned long lastDEF=0;
unsigned long lastHIJ=0;

void setup() {
  Serial.begin(BAUD_RATE);
  randomSeed(analogRead(A0)); 
}

void loop() {
  unsigned long now = millis();

  if (now - lastABC >= ABC_INTERVAL) {
    lastABC = now;
    float v = random(0, 10001) / 10000.0;  
    Serial.print("ABC:");
    Serial.println(v, 4);
  }

  if (now - lastDEF >= DEF_INTERVAL) {
    lastDEF = now;
    Serial.print("DEF:");
    Serial.println(random(-50, 51));  
  }

  if (now - lastHIJ >= HIJ_INTERVAL) {
    lastHIJ = now;
    Serial.print("HIJ:");
    Serial.println(random(0, 101));
  }
}