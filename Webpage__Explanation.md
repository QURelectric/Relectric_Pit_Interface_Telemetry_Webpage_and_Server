### Battery SOC Graph
This displays the Battery State of Charge of the past 30 seconds

### Temps Graph
This displays the Motor and Inverter temperatures of the past 30 seconds

### Flags

##### Motor
Temp displays OK or OVER TEMP this is signal directly from the motor controller, when reading OVER TEMP the text will be red

##### System
Traction will either displays OFF, OK, or LOW, these are signals directly from the motor controller

Direction will display either FORWARD, BACKWARD or NONE depending on the drive direction given by the motor controller

Break will display PEDAL, PARK, NONE, or BOTH, this signal is from the motor controller

Cntrl Temp will display OK or OVER TEMP, this signal is directly from the motor controller, when reading OVER TEMP the text will be red

Keyswitch volt will display UNDER OVER or NORMAL, this signal is directly from the motor controller

##### Fault
Code will display the current fault code from the motor controller

Level will display the current fault level from the motor controller


### Kart
Status will cycle through the powering of the kart, it will display RUNNING, CONTACTS CLOSING, POW READY, POW PRE-CHAGING, POW ENABLED

Odometer will display the odometer from the motor controller

Current will display the current going through the motor controller

Speed displays the speed value in the data base, this will either be from the GPS or the motor controller

Operating Time displays the current operating time of the motor controller

Lap time displays the current lap time plus the delta from the last lap time


### Controls
Driver Pit sends the signal to the driver to pit

Driver Warn sends an emergency signal to the driver, this must be defined by the driver and pit what this emergency will mean

Start Saved/End Save will start saving all data to a CSV file, this will continue even when the webpage is closed as long as the server is running


### Track
Displays an outline of the whole track and pit lane and places the karts GPS position onto the track