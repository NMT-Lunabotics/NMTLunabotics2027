unsigned long lastTime = 0;
const char* sensorName = "test";

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(10);
}

void loop() {
  unsigned long now = millis();

  if (now - lastTime >= 100) {
    lastTime = now;
    float fake = 5.0 + 2.0 * sin(now / 10.0);
    Serial.print(sensorName);
    Serial.print(":");
    Serial.println(fake, 3);
  }

  if (Serial.available() > 0) {
    String message = Serial.readStringUntil('\n');
    message.trim();

    if (message.length() > 0) {
      Serial.print("RECIVED: ");
      Serial.println(message);
    }
  }
}