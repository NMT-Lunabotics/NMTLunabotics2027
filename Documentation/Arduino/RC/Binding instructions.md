https://manuals.plus/asin/B09STCQCCF

### Controller binding
***

1. Put FS-iA6B into binding mode:

The FS-iA6B reviver has 4 rows, one row of (6) and three rows of (7). Rows are layout as (TOP-SOURCE-POWER-GROUND), 
Ignore the **TOP** row, below the (VCC/B) connect a wire between the **SOURCE** and **GROUND** pins.

***

2. Power reciver:

Power the **POWER** row using 5v, and ground the **GROUND** row.

***

3. Bind the reciver to the controller:

Once the reviver is powered it will start rapidly flashing. Hold the bind button the on the controller(circle button labeld bind key) and turn on the controller, after stopping the startup warning reciver will bind. 

***

4. Finish setup:

Controller can now be turned off, binding wire removed, and everything replugged in. 

***

### Wiring
***
The reciver is labled as (B/VCC, CH6, CH5, CH4, CH3, CH2, PP/CH1), for wiring connect three wires to the **TOP** row of the reciver. Connect arduino **RX1** to **B/VCC**, **CH6** to **5V**, and **CH5** to **GND**