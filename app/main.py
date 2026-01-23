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
from queue import Queue

import signal

import random

from . import ParseandExtractMap
# Import necessary modules for HTML responses and templating

app = FastAPI()
# Create an instance of the FastAPI class

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# Set up Jinja2 templates, specifying the directory where HTML templates are stored

active_connections = []




#Global Variables
configPath = "config.json"

#Dictionary format for data
#send_Data = {
#                    "batterySOC": 100, #[0,100]
#                    "MotorTemp": 0, #[0,255] value, [-40,+215] Celcius
#                    "InverterTemp": 0, #[0,255] value, [-40,+215] Celcius
#                    "LapTime": 0,
#                    "LapTimeDelta": 0,
#                    "FaultLevel": 0, #[0 fine, 4 warning, 3 Throttle down, 2 stopping, 1 Cut power]
#                    "FaultCode": 0, #[0,150]
#                    "MotorFlag": 0, #bitmask(BIT3: Motor 1 Overtemp, BIT7: Motor2 Overtemp)
#                    "SystemFlags": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], #bitmask(BIT0: SoC low traction, BIT1: SOC low hydraulic, BIT2: Reverse Direction, BIT3: Forward Direction, BIT4: Parking brake, BIT5: Pedal Break, BIT6: Controller Overtemp, BIT7: keyswitch overvolt, BIT8: Keyswitch undervolt, BIT9: Vehicle Running, BIT10: Traction Enabled, BIT11: Hydraulics Enabled, BIT12: Powering Enabled, BIT13: Powering ready, BIT14: Powering is Precharging, BIT15:  Main Contacting Closing)
#                    #BIT12 -> BIT14 -> BIT13 -> BIT15 -> BIT9
#                    #Powering enabled -> powering precharging -> powering ready -> main contacts closing -> vehicle running
#                    "Odometer": 0,
#                    "counter": 0,
#                    "Current": 0, #[-32768; +32767] ↔ [-3276.8; +3276.7]Arms
#                    "Speed": 0, #[[-32768; +32767] ↔ [-3276.8;+3276.7]km/h]
#                    "OperatingTime": 0,
#                    "Saving": False,
#                    "DriverPos": []
#}


config_Data_Queue = Queue()
data_Queue = Queue(maxsize=100)
save_File_Path_Queue = Queue()
save_Begun_Queue = Queue()
interval_Queue = Queue()
test_File_Path_Queue = Queue()

def extractConfig(path):
    if os.path.exists(path):
        with open(path, 'r') as file:
            data = json.load(file)
            return data
    else:
        print("Config File does not exist")
        print("Please create a config file and rerun the program")
        ShutdownServer()

#Test Function for the test file, all variables in the test file should be database with the same names
def extractJson(path):
    if os.path.exists(path):
            with open(path, 'r') as file:
                file_data = json.load(file)
                Data = {}
                Data["batterySOC"] = file_data.get("batterySOC",0)
                Data["MotorTemp"] = file_data.get("MotorTemp",0)
                Data["InverterTemp"] = file_data.get("InverterTemp",0)
                Data["LapTime"] = file_data.get("LapTime",0)
                Data["LapTimeDelta"] = file_data.get("LapTimeDelta",0)
                Data["FaultLevel"] = file_data.get("FaultLevel",0)
                Data["FaultCode"] = file_data.get("FaultCode",0)
                Data["MotorFlag"] = file_data.get("MotorFlag",0)
                Data["SystemFlags"] = file_data.get("SystemFlags",0)
                Data["Odometer"] = file_data.get("Odometer",0)
                Data["OperatingTime"] = file_data.get("OperatingTime",0)
                Data["Current"] = file_data.get("Current",0)
                Data["Speed"] = file_data.get("Speed",0)
                Data["DriverPos"] = file_data.get("DriverPose",None)
                return Data
    return None

#Create the save file
def StartSaveFile(savedirectory):
    now = datetime.datetime.now()
    fileCreationDate = now.strftime("%Y.%m.%d.%H.%M.%S")
    file_name = "KartData." + fileCreationDate + ".csv"
    path = os.path.join(savedirectory, file_name)
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
            data_copy = currentData.copy()
            flags = currentData.get("SystemFlags", [0]*16)
            if isinstance(flags, list):
                data_copy["SystemFlags"] = int(''.join(map(str, flags)), 2)
            keys = [
                "batterySOC", "MotorTemp", "InverterTemp", "LapTime", 
                "LapTimeDelta", "FaultLevel", "FaultCode", "MotorFlag", 
                "SystemFlags", "Odometer", "OperatingTime", "Current", "Speed"
            ]
            lineData = [str(data_copy.get(k,"")) for k in keys]
            file.write(",".join(lineData) + "\n")
        return 1
    except Exception as e:
        print(f"Failed to save Data : {e}")
        return 0
    

#Runs the save new data function onces a second
#This is run on a seperate thread as a daemon
def background_Data_Logger(saveInterval, jsonSource, save_path_queue: Queue, save_begun_queue: Queue, data_out_queue: Queue):
    print("Logger Started")
    save_Begun = False
    saveFile = None
    last_save_time = time.perf_counter()

    current_interval = saveInterval
    current_json_source = jsonSource

    while True:
        try:
            if not save_path_queue.empty():
                saveFile = save_path_queue.get()
            
            if not save_begun_queue.empty():
                save_Begun = save_begun_queue.get()

            if not interval_Queue.empty():
                current_interval = interval_Queue.get()
            
            # Check for test file path updates
            if not test_File_Path_Queue.empty():
                current_json_source = test_File_Path_Queue.get()

            save_data = extractJson(current_json_source) #Change this out when real database is made

            if save_data is not None:
                data_out_queue.put(save_data)

            current_time = time.perf_counter()
            if (current_time - last_save_time >= current_interval and save_Begun and saveFile is not None and save_data is not None):
                saveNewData(saveFile, save_data)
                last_save_time = current_time

            time.sleep(0.01)

        except Exception as e:
            print(f"Error in Backgrouns Logger: {e}")
            time.sleep(1)



def configSetting(configPath):

    required_keys = ["SaveFilePath", "TrackPathFile", "SaveIntervalSeconds"]

    data = extractConfig(configPath)

    missing_keys = [key for key in required_keys if key not in data]

    if missing_keys:
        print(f"Error: Missing required configuration keys: {', '.join(missing_keys)}")
        print("Please Ensure Config file has needed keys")
        ShutdownServer()

    config = {
        "SavePath": data["SaveFilePath"],
        "trackMap": data["TrackPathFile"],
        "interval": data["SaveIntervalSeconds"],
        "testing": data.get("Testing", False),
        "testDriverPos": data.get("TestKartPosition"),
        "test_File_Path": data.get("TestDataPath")
    }


    if config["testing"]:
        if config["testDriverPos"] is None:
            print("Warning: Testing mode enabled but 'TestKartPosition' not found")
        if config["test_File_Path"] is None:
            print("Warning: Testing mode enabled but 'TestDataPath' not found")


    return config

def configChangeCheck(configPath, config_queue: Queue):
        lastChangedTime = os.path.getmtime(configPath)
        while True:
            try:
                current_Modified_Time = os.path.getmtime(configPath)
                if current_Modified_Time != lastChangedTime:
                    new_config = configSetting(configPath)
                    config_queue.put(new_config)

                    interval_Queue.put(new_config["interval"])
                    if new_config["test_File_Path"]:
                        test_File_Path_Queue.put(new_config["test_File_Path"])


                    print("Config File has changed")
                    lastChangedTime = current_Modified_Time
                time.sleep(5)
            except Exception as e:
                print(f"Error in config check: {e}")
                time.sleep(5)

#Test function to slowly lower battery SOC for testing
def TestBatteryUse(currentBattery):
    battery = currentBattery - (0.0001 * float(random.randint(0,100)))
    if battery < 0:
        battery = 0
    return battery

def ShutdownServer():
    print("Server is shutting down")
    os.kill(os.getpid(), signal.SIGTERM)



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

    initial_config = configSetting(configPath)

    data_logger = threading.Thread(
        target=background_Data_Logger,
        args=(
            initial_config["interval"],
            initial_config["test_File_Path"],
            save_File_Path_Queue,
            save_Begun_Queue,
            data_Queue
        ),
        daemon=True
    )
    configCheck = threading.Thread(
        target=configChangeCheck,
        args=(configPath, config_Data_Queue),
        daemon=True
    )

    data_logger.start()
    configCheck.start()
    print("Background saver task created")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    import asyncio
    seconds = 0
    counter = 0
    batterySOC = 100
    saveBegun = None

    #How many seconds between sending data to the webpage
    updateTime = 0.04

    current_config = configSetting(configPath)
    SavePath = current_config["SavePath"]
    trackMap = current_config["trackMap"]
    interval = current_config["interval"]
    testing = current_config["testing"]
    testDriverPos = current_config["testDriverPos"]
    test_File_Path = current_config["test_File_Path"]


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
        nonlocal saveBegun, SavePath
        try:
            while True:
                recieved_Data = await websocket.receive_json()

                if recieved_Data.get("DriverPit") == 1:
                    print("Driver Pit Signal Recieved ")
                
                if recieved_Data.get("DriverEmergency") == 1:
                    print("Driver Emergency") 
                
                if recieved_Data.get("StartSave") == 1:
                    newSaveFile = StartSaveFile(SavePath)
                    if newSaveFile:
                        save_File_Path_Queue.put(newSaveFile)
                        saveBegun = True
                        save_Begun_Queue.put(True)
                        print(f"Started Saving to: {newSaveFile}")
                
                if recieved_Data.get("EndSave") == 1:
                    saveBegun = False
                    save_Begun_Queue.put(False)
                    print("Stopped Saving")
                        
        except Exception as e:
             print(f"Receiver error: {e}")


    #Starts the Asynchronous reciever function  
    receive_task = asyncio.create_task(receiver())

    
    try:
        #Continously sends data to the web page
        while True:
            #Checks if the websocket is still connected, if no the loop breaks
            if websocket.client_state.value == 1:

                if not config_Data_Queue.empty():
                    new_config = config_Data_Queue.get()
                    SavePath = new_config["SavePath"]
                    if trackMap != new_config["trackMap"]:
                        trackMap = new_config["trackMap"]
                        try:
                            track,pit,referenceMin,referenceMax = asyncio.to_thread(ParseandExtractMap.ExtractKML(trackMap))
                            track_data = {"track":track, "pit":pit}
                            await websocket.send_json(track_data)
                        except Exception as e:
                            print(f"Error in kml reader: {e}")
                            track = []
                            pit = []

                    interval = new_config["interval"]
                    testing = new_config["testing"]
                    testDriverPos = new_config["testDriverPos"]
                    test_File_Path = new_config["test_File_Path"]
                    print("Config updated in websocket")
                    interval_Queue.put(interval)
                    test_File_Path_Queue.put(test_File_Path)


                if not data_Queue.empty():
                    current_Data = data_Queue.get()
                else:
                    continue

                try:
                    if testing:
                        counter += 1
                        current_Data["DriverPos"] = testDriverPos
                        current_Data["batterySOC"] = TestBatteryUse(batterySOC)
                        batterySOC = current_Data["batterySOC"]
                        current_Data["OperatingTime"] = seconds
                        if counter % (1 / updateTime) == 1:
                            seconds += 1

                    

                    #Normalizes the kart position given in LON and LAT into the nomormalized track layout
                    if current_Data["DriverPos"]:
                        current_Data["DriverPos"] = ParseandExtractMap.normalizeKartPosition(current_Data["DriverPos"],referenceMin,referenceMax)

                    current_Data["Saving"] = saveBegun
                    #Sends the current data to the webserver
                    await websocket.send_json(current_Data)
                except Exception as Frame_Error:
                    print(f"Error processing data frame: {Frame_Error}")
                
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
