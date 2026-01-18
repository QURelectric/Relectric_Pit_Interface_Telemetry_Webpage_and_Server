import asyncio
import sys
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastapi.staticfiles import StaticFiles

import json
import os
import datetime
import time
import threading

import random

from . import ParseandExtractMap
# Import necessary modules for HTML responses and templating

app = FastAPI()
# Create an instance of the FastAPI class

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# Set up Jinja2 templates, specifying the directory where HTML templates are stored

active_connections = []


# Test Variables
test_File_Path = "C:\\Users\\starl\\OneDrive\\Desktop\\School\\2nd_Year\\Relectric\\WebServerBasedTelemtryUI\\UI\\TestData.json"
test_save_path = "C:\\Users\\starl\\OneDrive\\Desktop\\School\\2nd_Year\\Relectric\\WebServerBasedTelemtryUI\\UI"
testDriverPos = [40.43788230494788, -86.94481112554759]
testing = True


#Global Variables
trackMap = "purduePathTest.kml"
SavePath = ""
data_lock = threading.Lock()

#Dictionary format for data
send_Data = {
                    "batterySOC": 100, #[0,100]
                    "MotorTemp": 0, #[0,255] value, [-40,+215] Celcius
                    "InverterTemp": 0, #[0,255] value, [-40,+215] Celcius
                    "LapTime": 0,
                    "LapTimeDelta": 0,
                    "FaultLevel": 0, #[0 fine, 4 warning, 3 Throttle down, 2 stopping, 1 Cut power]
                    "FaultCode": 0, #[0,150]
                    "MotorFlag": 0, #bitmask(BIT3: Motor 1 Overtemp, BIT7: Motor2 Overtemp)
                    "SystemFlags": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], #bitmask(BIT0: SoC low traction, BIT1: SOC low hydraulic, BIT2: Reverse Direction, BIT3: Forward Direction, BIT4: Parking brake, BIT5: Pedal Break, BIT6: Controller Overtemp, BIT7: keyswitch overvolt, BIT8: Keyswitch undervolt, BIT9: Vehicle Running, BIT10: Traction Enabled, BIT11: Hydraulics Enabled, BIT12: Powering Enabled, BIT13: Powering ready, BIT14: Powering is Precharging, BIT15:  Main Contacting Closing)
                    #BIT12 -> BIT14 -> BIT13 -> BIT15 -> BIT9
                    #Powering enabled -> powering precharging -> powering ready -> main contacts closing -> vehicle running
                    "Odometer": 0,
                    "counter": 0,
                    "Current": 0, #[-32768; +32767] ↔ [-3276.8; +3276.7]Arms
                    "Speed": 0, #[[-32768; +32767] ↔ [-3276.8;+3276.7]km/h]
                    "OperatingTime": 0,
                    "Saving": False,
                    "DriverPos": []
                }
seconds = 0
counter = 0
batterySoC = 100
saveFile = ""
saveBegun = False



#Test Function for the test file, all variables in the test file should be database with the same names
def extractJson(path,Data):
    if os.path.exists(path):
            with open(path, 'r') as file:
                file_data = json.load(file)
                Data["batterySOC"] = file_data["batterySOC"]
                Data["MotorTemp"] = file_data["MotorTemp"]
                Data["InverterTemp"] = file_data["InverterTemp"]
                Data["LapTime"] = file_data["LapTime"]
                Data["LapTimeDelta"] = file_data["LapTimeDelta"]
                Data["FaultLevel"] = file_data["FaultLevel"]
                Data["FaultCode"] = file_data["FaultCode"]
                Data["MotorFlag"] = file_data["MotorFlag"]
                Data["SystemFlags"] = file_data["SystemFlags"]
                Data["Odometer"] = file_data["Odometer"]
                Data["OperatingTime"] = file_data["OperatingTime"]
                Data["Current"] = file_data["Current"]
                Data["Speed"] = file_data["Speed"]
    return Data

#Create the save file
def StartSaveFile(savedirectory):
    now = datetime.datetime.now()
    fileCreationDate = now.strftime("%Y.%m.%d.%H.%M.%S")
    file_name = "KartData." + fileCreationDate + ".csv"
    path = savedirectory + "\\" + file_name
    try:
        with open(path,'w') as file:
            keys = [
                "batterySOC", "MotorTemp", "InverterTemp", "LapTime", 
                "LapTimeDelta", "FaultLevel", "FaultCode", "MotorFlag", 
                "SystemFlags", "Odometer", "OperatingTime", "Current", "Speed"
            ]
            file.write(",".join(keys) + "\n")
            return path
    except Exception as e:
        print("Save File Failed to Generate")
        return None

#Appends data to the current save file into a csv format
def saveNewData(path,currentData):
    try:
        with open(path, 'a') as file:
            currentData["SystemFlags"] = int(''.join(map(str,currentData["SystemFlags"])),2)
            keys = [
                "batterySOC", "MotorTemp", "InverterTemp", "LapTime", 
                "LapTimeDelta", "FaultLevel", "FaultCode", "MotorFlag", 
                "SystemFlags", "Odometer", "OperatingTime", "Current", "Speed"
            ]
            lineData = [str(currentData.get(k,"")) for k in keys]
            file.write(",".join(lineData) + "\n")
        return 1
    except Exception as e:
        print(f"Failed to save Data : {e}")
        return 0
    

#Runs the save new data function onces a second
#This is run on a seperate thread as a daemon
def background_Data_Logger():
    print("Logger Started")
    global send_Data
    global saveFile

    last_save_time = time.time()

    while True:
        try:
            save_data = extractJson(test_File_Path,send_Data)
            with data_lock:
                send_Data = save_data.copy()
            current_time = time.time()
            if current_time - last_save_time >= 1.0 and saveBegun:
                saveNewData(saveFile, save_data)
                last_save_time = current_time

            time.sleep(0.01)

        except Exception as e:
            print(f"Error in Backgrouns Logger: {e}")
            time.sleep(1)


#Test function to slowly lower battery SOC for testing
def TestBatteryUse(currentBattery):
    battery = currentBattery - (0.0001 * float(random.randint(0,100)))
    if battery < 0:
        battery = 0
    return battery





# Most Basic Example
@app.get("/", response_class=HTMLResponse)
# Define a GET endpoint at the root URL (Eg http://localhost:8000/) 
# and specify that it returns an HTML response
async def read_root(request: Request):
    # Define an asynchronous function to handle requests to this endpoint
    return templates.TemplateResponse("index.html", {"request": request, "message": "Hello World"})
    # Return a simple JSON response using the template "index.html" with a message


@app.on_event("startup")
async def startup_event():
    global SavePath
    if testing:
        SavePath = test_save_path
    thread = threading.Thread(target=background_Data_Logger,daemon=True)
    thread.start()
    print("Background saver task created")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    import asyncio
    global send_Data
    Path = ""
    global seconds
    global testing
    global counter
    global batterySoC
    global saveBegun
    global saveFile

    #How many seconds between sending data to the webpage
    updateTime = 0.04


    referenceMin = []
    referenceMax = []

    #Used when extracting from a point based kml file
    pitEntrancePoint = 24
    pitExitPoint = 32

    #Gets the track layout only at the initial websocket connection
    try:
        track,pit,referenceMin,referenceMax = ParseandExtractMap.ExtractKML(trackMap)
        track_data = {"track":track, "pit":pit}
        await websocket.send_json(track_data)
    except Exception as e:
        print(f"Error in kml reader: {e}")
        track = []
        pit = []

    #An asynchrnous reciever to recieve button data from the web page
    async def receiver():
        global saveBegun
        global saveFile
        try:
            while True:
                recieved_Data = await websocket.receive_json()
                if recieved_Data.get("DriverPit") == 1:
                    print("Driver Pit Signal Recieved ")
                if recieved_Data.get("DriverEmergency") == 1:
                    print("Driver Emergency") 
                if recieved_Data.get("StartSave") == 1:
                    saveFile = StartSaveFile(SavePath)
                    saveBegun = True
                if recieved_Data.get("EndSave") == 1:
                    saveBegun = False
                        
        except Exception as e:
             print(f"Receiver error: {e}")

    #Starts the Asynchronous reciever function  
    receive_task = asyncio.create_task(receiver())

    
    try:
        #Continously sends data to the web page
        while True:
            #Checks if the websocket is still connected, if no the loop breaks
            if websocket.client_state.value == 1:
                current_Data = send_Data.copy()
                
                if testing:
                    counter += 1
                    current_Data["DriverPos"] = testDriverPos
                    current_Data["batterySOC"] = TestBatteryUse(batterySoC)
                    batterySoC = current_Data["batterySOC"]
                    current_Data["OperatingTime"] = seconds
                    if counter % (1/updateTime) == 1:
                        seconds += 1
                #Normalizes the kart position given in LON and LAT into the nomormalized track layout 
                current_Data["DriverPos"] = ParseandExtractMap.normalizeKartPosition(current_Data["DriverPos"],referenceMin,referenceMax)
                current_Data["Saving"] = saveBegun
                #Sends the current data to the webserver
                await websocket.send_json(current_Data)
                
            else:
                print("Webpage Closed, waiting for webpage to reopen")
                if saveBegun:
                    print("Program Still Saving Data")
                break

            await asyncio.sleep(updateTime)
    except Exception as e:
         print(f"Connection/Loop Failed: {e}")
    finally:

        #Once the loop is broken the ansychronous reciever is shutdown
        if not receive_task.done():
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass
        print("WebSocket Session Cleaned")
