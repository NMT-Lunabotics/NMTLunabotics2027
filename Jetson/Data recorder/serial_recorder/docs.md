This system records data sent from an Arduino over serial on the jetson. Every ID listed in the config is saved to its own file, one file per ID per day, with each row stored as timestamp,data.
Data from the Arduino must look like ID:data with no spaces. A space or newline ends the data.

----------------------------------------------------------------------
1. Install required package on target device
----------------------------------------------------------------------

sudo apt update && sudo apt install -y python3-serial

----------------------------------------------------------------------
2. Add script, config and startup files, and make py file executable
----------------------------------------------------------------------

sudo nano /etc/systemd/system/serial-recorder.service

sudo nano /etc/serial_recorder.conf
sudo chmod 600 /etc/hotspot.conf

sudo nano /usr/local/bin/serial_recorder.py
sudo chmod +x /usr/local/bin/serial_recorder.py

----------------------------------------------------------------------
3. Start the startup services
----------------------------------------------------------------------

sudo systemctl daemon-reload
sudo systemctl enable serial-recorder.service
sudo systemctl start serial-recorder.service

sudo systemctl status serial-recorder.service
