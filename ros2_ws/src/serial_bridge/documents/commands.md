Install required packages
```
arduino-cli core install arduino:avr
```

ros2 param set /serial_manager serial.microcontrollers.main.restart true
ros2 param set /serial_manager serial.microcontrollers.main.reset true
ros2 param set /serial_manager serial.microcontrollers.main.upload true