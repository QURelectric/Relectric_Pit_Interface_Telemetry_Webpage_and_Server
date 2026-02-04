console.log("Scripts.js loaded");

const el = {
                MotorTempWarning: null,
                traction: null,
                direction: null,
                break: null,
                controllerTempWarning: null,
                keyVoltage: null,
                status: null,
                faultCode: null,
                faultLevel: null,
                odometer: null,
                current: null,
                speed: null,
                uptime: null,
                lap: null,
                saveButton: null,
                logIndicator: null,
                logText: null,
                pitButton: null,
                warnButton: null
            };

            const graphInterval = 40 //How many datapoints you want to be shown
            //Change coefficients to change where the latest data point is placed on the graphs
            const RightBuffer = 0.25 * graphInterval;
            const LeftBuffer = 0.75 * graphInterval;
            const zeroPoint = LeftBuffer;

            const MAX_DATA_POINTS = graphInterval * 1200;
            const CHART_UPDATE_INTERVAL = 25; //milliseconds
            let chartUpdateQueued = false;
            let pendingUpdates = {
                battery: null,
                motorTemp: null,
                inverterTemp: null
            };

            const chartOptions = {
                animation: false,
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y : { min: 0, max: 100, ticks: { stepSize: 10}},
                    x : {
                        type: "linear",
                        min: 0,
                        max: 40,
                        ticks: {
                            stepSize: 10,
                            display: true,
                            callback: (v) => v - zeroPoint
                        }
                    }
                }
            }
            const chartOptionsNoLegend = {
                animation: false,
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                },
                scales: {
                    y : { min: 0, max: 100, ticks: { stepSize: 10}},
                    x : {
                        type: "linear",
                        min: 0,
                        max: 40,
                        ticks: {
                            stepSize: 10,
                            display: true,
                            callback: (v) => v - zeroPoint
                        }
                    }
                }
            }



            //Battery State of charge graph data and scale format
            const ctxBattery = document.getElementById("BatterySOC_Graph_ID").getContext('2d')
            const BatterySOC_Graph = new Chart(ctxBattery, {
                type: 'line',
                data: {
                    datasets: [{
                        label: 'Battery SOC',
                        data: [],
                        tension: 0.1,
                        pointRadius: 0,
                        showLine: true,
                        fill: {
                            target: 'origin',
                            below: 'rgb(29, 45, 68)'

                        }

                    }]
                },
                options: chartOptionsNoLegend
                });

            //Motor and Inverter Temp graph data and scale format
            const ctxTemps = document.getElementById("Temps_Graph_ID").getContext('2d')
            const Temps_Graph = new Chart(ctxTemps, {
                type: 'line',
                data: {
                    datasets: [{
                        label: 'MotorTemp',
                        data: [],
                        tension: 0,
                        pointRadius: 1
                    },
                    {
                        label: 'InverterTemp',
                        data: [],
                        tension: 0,
                        pointRadius: 1
                    }]
                },
                options: chartOptions
                });

            const ctxTrack = document.getElementById("Track_Graph_ID").getContext("2d")
            const Track = new Chart(ctxTrack, {
                type: 'line',
                data: {
                    datasets: [{
                        label: 'track',
                        data: [],
                        tension: 0.4,
                        borderColor: 'rgb(29, 45, 68)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderWidth: 5,
                        pointRadius: 0,  // SET TO 0 - no points, just line
                        showLine: true,
                        borderCapStyle: 'round',
                        order: 3
                    },
                    {
                        label: 'pit',
                        data: [],
                        tension: 0.4,
                        borderColor: 'rgb(29, 45, 68)',
                        backgroundColor: 'rgba(255, 165, 0, 0.2)',
                        borderWidth: 5,
                        pointRadius: 0,  // SET TO 0 - no points, just line
                        showLine: true,
                        borderCapStyle: 'round',
                        order: 2
                    },
                    {
                        label: 'trackBorder',
                        data: [],
                        tension: 0.4,
                        borderColor: 'rgb(179, 200, 219)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderWidth: 10,
                        pointRadius: 0,  // SET TO 0 - no points, just line
                        showLine: true,
                        borderCapStyle: 'round',
                        borderJoinStyle: 'round',
                        order: 4
                    },
                    {
                        label: 'pitBorder',
                        data: [],
                        tension: 0.4,
                        borderColor: 'rgb(179, 200, 219)', 
                        backgroundColor: 'rgba(255, 165, 0, 0.2)',
                        borderWidth: 10,
                        pointRadius: 0,  // SET TO 0 - no points, just line
                        showLine: true,
                        borderCapStyle: 'round',
                        borderJoinStyle: 'round',
                        order: 4
                    },
                    {
                            label: 'driver',
                            data: [],
                            tension: 0,
                            borderColor: 'rgba(255, 99, 132, 0.5)',
                            backgroundColor: 'rgb(255, 99, 132)',
                            borderWidth: 0,
                            pointRadius: 10,
                            pointStyle: 'circle',
                            showLine: false,
                            order: 1
                        },]
                },
                options: {
                    animation: false,
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            enabled: true,
                            callbacks: {
                                title: function(context) {
                                    return context[0].raw.name || '';
                                },
                                label: function(context) {
                                    return `x: ${context.parsed.x.toFixed(2)}, y: ${context.parsed.y.toFixed(2)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: { 
                            min: 0, 
                            max: 1, 
                            ticks: { display: false },
                            border: { display: false},
                            grid: { display: false}
                        },
                        x: {
                            type:'linear',
                            min: 0,
                            max: 1,
                            ticks: { display: false },
                            border: { display: false},
                            grid: { display: false}
                        }
                    }
                }
            });

            console.log('Track chart config:', Track.config);
            console.log('Track datasets:', Track.data.datasets);
            console.log('Dataset 0 borderWidth:', Track.data.datasets[0].borderWidth);
            console.log('Dataset 1 borderWidth:', Track.data.datasets[1].borderWidth);

            function updateDataRelatively(chart, newValue, datasetIndex) {
                const dataset = chart.data.datasets[datasetIndex].data;

                for (let i = 0; i < dataset.length; i++){
                    dataset[i].x -= (CHART_UPDATE_INTERVAL/1000);
                }

                dataset.push({x: zeroPoint, y: newValue});


                while (dataset.length > 0 && dataset[0].x < 0) {
                    dataset.shift();
                }

                while (dataset.length > MAX_DATA_POINTS) {
                    dataset.shift();
                }
            }

            function updateCharts(){
                if (pendingUpdates.battery !== null){
                    updateDataRelatively(BatterySOC_Graph,pendingUpdates.battery,0);
                }
                if (pendingUpdates.motorTemp !== null){
                    updateDataRelatively(Temps_Graph, pendingUpdates.motorTemp,0);
                }
                if (pendingUpdates.InverterTemp !== null){
                    updateDataRelatively(Temps_Graph, pendingUpdates.inverterTemp,1);
                }
                if (pendingUpdates.battery !== null || pendingUpdates.motorTemp !== null || pendingUpdates.inverterTemp !== null){
                    BatterySOC_Graph.update('none');
                    Temps_Graph.update('none');
                }

                pendingUpdates.battery = null;
                pendingUpdates.motorTemp = null;
                pendingUpdates.inverterTemp = null;
                chartUpdateQueued = false;
            }

            function sendCommand(cmd){
                if(ws.readyState ===  WebSocket.OPEN){
                    ws.send(JSON.stringify(cmd));
                    console.log("Sent Command:",cmd);
                }
            }

            function DriverPit() {
                if(el.pitButton.innerText == "Driver Pit"){
                    el.pitButton.innerText = "Confirm";
                    return;
                }     
                if(el.pitButton.innerText == "Confirm"){
                    sendCommand({DriverPit: 1});
                    el.pitButton.innerText = "Driver Pit";
                    return;
                } 
            }

            function DriverEmergency() { 
                if(el.warnButton.innerText == "Driver Warn"){
                    el.warnButton.innerText = "Confirm";
                    return;
                }     
                if(el.warnButton.innerText == "Confirm"){
                    sendCommand({DriverEmergency: 1});
                    el.warnButton.innerText = "Driver Warn";
                    return;
                } 
                sendCommand({DriverEmergency: 1});
            
            }

            function StartSave() {
                sendCommand({ StartSave: 1 });
                el.saveButton.innerText = "End Save";
                el.saveButton.onclick = EndSave;
                el.logIndicator.style.backgroundColor = "red";
                el.logText.innerText = "Logging in Progress...";
            }
            
            function EndSave() {
                sendCommand({ EndSave: 1 });
                el.saveButton.innerText = "Start Save";
                el.saveButton.onclick = StartSave;
                el.logIndicator.style.backgroundColor = "grey";
                el.logText.innerText = "";
            }


            function updateTrackLayout(trackPoints,pitPoints) {
                Track.data.datasets[0].data = trackPoints.map(point => ({
                    x: point[2],
                    y: point[1],
                    label: point[0]
                }));
                Track.data.datasets[1].data = pitPoints.map(point => ({
                    x: point[2],
                    y: point[1],
                    label: point[0]
                }));
                Track.data.datasets[2].data = trackPoints.map(point => ({
                    x: point[2],
                    y: point[1],
                    label: point[0]
                }));
                Track.data.datasets[3].data = pitPoints.map(point => ({
                    x: point[2],
                    y: point[1],
                    label: point[0]
                }));
                Track.update('none');
            }

            function updateDriverPos(Position) {
                if (!Position || Position.length < 2){
                    return;
                }
                Track.data.datasets[4].data = [{
                    x: Position[1],
                    y: Position[0]
                }];
                Track.update('none');
            }



            const ws = new WebSocket("ws://" + location.host + "/ws");

            ws.onopen = () => {
                console.log("WebSocket Connected ✅");
                // Cache DOM elements after connection
                //In Spanish
                el.MotorTempWarning = document.getElementById("MotorTempWarning");
                el.traction = document.getElementById("traction");
                el.direction = document.getElementById("direction");
                el.break = document.getElementById("break");
                el.controllerTempWarning = document.getElementById("controllerTempWarning");
                el.keyVoltage = document.getElementById("keyVoltage");
                el.status = document.getElementById("status");
                el.faultCode = document.getElementById("faultCode");
                el.faultLevel = document.getElementById("faultLevel");
                el.odometer = document.getElementById("odometer");
                el.current = document.getElementById("current");
                el.speed = document.getElementById("speed");
                el.uptime = document.getElementById("uptime");
                el.lap = document.getElementById("lap");
                el.saveButton = document.getElementById("saveButton");
                el.logIndicator = document.getElementById("logIndicator");
                el.logText = document.getElementById("logText");
                el.pitButton = document.getElementById("PitButton");
                el.warnButton = document.getElementById("WarnButton");
            };


            //When a message is recieved from the websock
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data)

                //parseFloat ensures the json value is in a float format
                pendingUpdates.battery = parseFloat(data.batterySOC);
                pendingUpdates.motorTemp = parseFloat(data.MotorTemp);
                pendingUpdates.inverterTemp = parseFloat(data.InverterTemp);


                if (!chartUpdateQueued) {
                    chartUpdateQueued = true;
                    setTimeout(updateCharts, CHART_UPDATE_INTERVAL);
                }


                if(data.hasOwnProperty('track')) {
                    updateTrackLayout(data.track,data.pit);

                }
                let pos = [0,0]
                pos = data.DriverPos
                updateDriverPos(pos);





                
                
                //These if statements are for the specific HyPer-Drive x1 motor controller
                if(data.SystemFlags) {
                    const flags = data.SystemFlags
                    el.MotorTempWarning.innerText = data.MotorFlag == 1 ? "OVER TEMP" : "OK";
                    el.MotorTempWarning.style.color = data.MotorFlag == 1 ? "red" : "";

                    el.traction.innerText = flags[10] == 0 ? "OFF" : (flags[0] == 1 ? "LOW" : "OK");
                    el.direction.innerText = flags[2] == 1 ? "REVERSE" : (flags[3] == 1 ? "FORWARD" : "NONE");
                    
                    let brakeStatus = "NONE";
                    if (flags[4] == 1 && flags[5] == 1) brakeStatus = "BOTH";
                    else if (flags[4] == 1) brakeStatus = "PARK";
                    else if (flags[5] == 1) brakeStatus = "PEDAL";
                    el.break.innerText = brakeStatus;

                    el.controllerTempWarning.innerText = flags[6] == 1 ? "OVER TEMP" : "OK";
                    el.controllerTempWarning.style.color = flags[6] == 1 ? "red" : "";

                    el.keyVoltage.innerText = flags[7] == 1 ? "OVER" : (flags[8] == 1 ? "UNDER" : "NORMAL");

                    let status = "OFF";
                    if (flags[9] == 1) status = "RUNNING";
                    else if (flags[15] == 1) status = "CONTACTS CLOSING";
                    else if (flags[13] == 1) status = "POW READY";
                    else if (flags[14] == 1) status = "POW PRE-CHARGING";
                    else if (flags[12] == 1) status = "POW ENABLED";
                    el.status.innerText = status;
                }

                el.faultCode.innerText = data.FaultCode;
                el.faultLevel.innerText = data.FaultLevel;
                el.odometer.innerText = data.Odometer;
                el.current.innerText = data.Current;
                el.speed.innerText = data.Speed;
                el.uptime.innerText = data.OperatingTime;

                const sign = data.LapTimeDelta >= 0 ? "+" : "-";
                const value = Math.abs(data.LapTimeDelta);
                el.lap.innerText = data.LapTime + " " + sign + " " + value;

                if (data.Saving == true){
                    el.saveButton.innerText = "End Save";
                    el.saveButton.onclick = EndSave;
                    el.logIndicator.style.backgroundColor = "red";
                    el.logText.innerText = "Logging in Progress...";
                }else {
                    el.saveButton.innerText = "Start Save";
                    el.saveButton.onclick = StartSave;
                    el.logIndicator.style.backgroundColor = "grey";
                    el.logText.innerText = "";
                }

            };
            ws.onerror = (err) => console.error("WebSocket Error ❌", err);