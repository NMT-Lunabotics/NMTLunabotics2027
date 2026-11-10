This system starts the serial_manager node during the inital jetson initaliztion. Allowing runs to be recorded and for sensor data to be logged. This is only ment for logging purposes, anything besides that will kill this inital instance. 

--------------------------------------------------------------------------------
1. Add the linux serivice, and paste contents of serial_bridge.service into it
- Note that the service will need to be updated to match your systems username
--------------------------------------------------------------------------------

sudo nano /etc/systemd/system/serial_bridge.service

--------------------------------------------------------------------------------
2. Start the startup services
--------------------------------------------------------------------------------

sudo systemctl daemon-reload
sudo systemctl enable serial_bridge.service
sudo systemctl start serial_bridge.service

sudo systemctl status serial_bridge.service