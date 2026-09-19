# Example code to send command to arduino 

#import required packages and moduals and setup serial and cli tools.
import sys, time; from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent; sys.path.insert(0, str(ROOT))
from Arduino.arduino_cli_old.cli_old import arduinoConsole
from Arduino.arduino_serial_commuication_old.arduino_serial_commuication_old import serialCommands

# Initialize arduino and serial classes with our deseried settings, and run our compile/upload function.
#arduino = arduinoConsole(sketch_path = ROOT/"system_operations"/"remote_rc_serial"/"host_sheild_test"/"host_sheild_test.ino", board="arduino:avr:mega")
arduino = arduinoConsole(sketch_path = ROOT/"Arduino"/"system_control_old"/"system_control_old.ino", board="arduino:avr:mega")
serial = serialCommands()
arduino.compile_and_upload()


# NOTE serial feedback is blocking, you will not recive serial error messages
#feedback = serial.read_command_feedback()
#if feedback:
#    for packet in feedback: 
#        print(packet)


while True:
    #serial.send_command("S", [180])
    #time.sleep(0.5)
    #serial.send_command("S", [0])
    #time.sleep(0.5)



    value = serial.read_serial()
    if value: print(value)