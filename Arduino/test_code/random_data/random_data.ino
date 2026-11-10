const unsigned long BAUD_RATE=115200;

const unsigned long ABC_INTERVAL=10;
const unsigned long DEF_INTERVAL=5000;
const unsigned long HIJ_INTERVAL=1000;

unsigned long lastABC=0;
unsigned long lastDEF=0;
unsigned long lastHIJ=0;

void setup() {
  Serial.begin(BAUD_RATE);
  randomSeed(analogRead(A0));
}

void loop() {
  unsigned long now=millis();

  if (now-lastABC>=ABC_INTERVAL) {
    lastABC=now;
    uint16_t v=random(0, 10001);
    Serial.print("ABC");
    Serial.write((uint8_t*)&v, sizeof(v));
  }

  if (now-lastDEF>=DEF_INTERVAL) {
    lastDEF=now;
    int16_t v=random(-50, 51);
    Serial.print("DEF");
    Serial.write((uint8_t*)&v, sizeof(v));
  }

  if (now-lastHIJ>=HIJ_INTERVAL) {
    lastHIJ=now;
    uint8_t v=random(0, 101);
    Serial.print("HIJ");
    Serial.write(&v, sizeof(v));
  }
}