from bs4 import BeautifulSoup
import numpy as np
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter

#Point Naming Convention 
    #All points should be created in order 
        #for example in google earth the points should be in series
        #so that connecting them in that order would create the track
    #Points to define the track cannot have the letter p in them
    #Points to define the pit must have the letter p in them
        #Pit points must also follow the ordering convention
    #Using the point system you must manually define the points where the pit connects to the main track

#Line and Polygon Convention 
    #If you're using paths and polygons to define your track and pit
    #The track should be defined using a closed loop polygon
        #No specific naming convention is needed
    #The pit should be defined using an open ended path
        #No specific naming convention is needed
    #Using the line and polygon system you do not need to define the coordinates where the pit and track connect
        #However you must have points in the pit line where it connects to the track polygon

def ExtractKML(kmlfile,pitEntrace=0,pitExit=0):
    with open(kmlfile, 'r') as f: 
        kml_content = f.read()
    soup = BeautifulSoup(kml_content, 'xml')

    LineString = soup.find_all('LineString')
    polygon = soup.find_all('Polygon')
    point = soup.find_all('Placemark')
    if LineString and polygon: 
        print("Using line and polygon extraction")
        track, pit = extractKMLPointsFromPathsandPolygons(kmlfile)
        nt,np,min,max = normalizeTrackPoints(track,pit)
        nt.append(nt[0])
        return nt,np,min,max
    elif point:
        print("Using point extraction")
        track, pit = extractKMLPointsFromPoints(kmlfile)
        nt,np,min,max = normalizeTrackPoints(track,pit)
        anp = addPitAttchmentPoints(nt,np,pitEntrace,pitExit)
        return nt, anp, min, max
    else:
        print("No valid points found")
        


def extractKMLPointsFromPathsandPolygons(kmlFile):
    kml_content = []
    trackPoints = []
    pitPoints = []
    with open(kmlFile, 'r') as f: 
        kml_content = f.read()
    soup = BeautifulSoup(kml_content, 'xml')

    for linestring in soup.find_all('LineString'):
        coords_elem = linestring.find('coordinates')
        if coords_elem:
            pitPoints = parseLineandPolygon(coords_elem.text)
    for polygon in soup.find_all('Polygon'):
        #only use the outer boundary
        coords_elem = []
        outer = polygon.find('outerBoundaryIs')
        if outer:
            coords_elem = outer.find('coordinates')
            if coords_elem:
                trackPoints = parseLineandPolygon(coords_elem.text)
    return trackPoints, pitPoints


        
def parseLineandPolygon(raw_coord):
    processed_Coord = []
    coord_strings = raw_coord.split()
    for coord in coord_strings:
        part = coord.split(',')
        if len(part) >= 2:
            lon = part[0]
            lat = part[1]
            processed_Coord.append([0,lat,lon])
    return processed_Coord


def extractKMLPointsFromPoints(kmlFile):
    kml_content = []
    trackPoints = []
    pitPoints = []
    reference = []
    with open(kmlFile, 'r') as f: 
        kml_content = f.read()
    soup = BeautifulSoup(kml_content, 'xml')
    # This finds every Placemark and extracts its Name and Coordinates
    for placemark in soup.find_all('Placemark'):
        name = placemark.find('name').get_text() if placemark.find('name') else "No Name"
        coords = placemark.find('coordinates').get_text().strip() if placemark.find('coordinates') else "No Coords"
        
        # KML coordinates are: Longitude, Latitude, Altitude
        parts = coords.split(',')
        if len(parts) >= 2:
            lon = parts[0]
            lat = parts[1]
            if name.lower() == "reference":
                reference = [name,lat,lon]
            else:
                if "p" in name:
                    pitPoints.append([name,lat,lon])
            
                else:
                    trackPoints.append([name,lat,lon])
    #Needed so the graph will close the loop
    trackPoints.append(trackPoints[0])
    return trackPoints,pitPoints

def normalizeTrackPoints(track,pit,desiredSpacing=0.0075):
    #LAT is North South
    #LON is West East
    MinLat = min([(min(track,key=lambda x:x[1]))[1],(min(pit,key=lambda x:x[1]))[1]])
    MinLon = min([(min(track,key=lambda x:x[2]))[2],(min(pit,key=lambda x:x[2]))[2]])

    #reference point is in the bottom left
    # => must use min LAT and LON
    
    referencePos = [MinLat,MinLon]


    MaxLat = max([(max(track,key=lambda x:x[1]))[1],(max(pit,key=lambda x:x[1]))[1]])
    MaxLon = max([(max(track,key=lambda x:x[2]))[2],(max(pit,key=lambda x:x[2]))[2]])

    maxPos = [MaxLat,MaxLon]

    normalizedTrack = []
    for element in track:
        #LAT first
        normalizedLAT = (float(element[1]) - float(referencePos[0])) / ((float(MaxLat) - float(referencePos[0])))
        normalizedLAT = 0.1 + (normalizedLAT * 0.8)

        normalizedLON = 1 - ((float(element[2]) - float(referencePos[1])) / ((float(MaxLon) - float(referencePos[1]))))
        normalizedLON = 0.1 + (normalizedLON * 0.8)

        normalizedTrack.append([element[0],normalizedLAT,normalizedLON])

    normalizedPit = []
    for element in pit:
        #LAT first
        normalizedLAT = (float(element[1]) - float(referencePos[0])) / ((float(MaxLat) - float(referencePos[0])))
        normalizedLAT = 0.1 + (normalizedLAT * 0.8)
        
        normalizedLON = 1 - ((float(element[2]) - float(referencePos[1])) / ((float(MaxLon) - float(referencePos[1]))))
        normalizedLON = 0.1 + (normalizedLON * 0.8)

        normalizedPit.append([element[0],normalizedLAT,normalizedLON])

    interp_track = interpolatePoints(normalizedTrack,spacing=desiredSpacing)
    interp_pit = interpolatePoints(normalizedPit,spacing=desiredSpacing)
    pit_Entrance = interp_pit[0]
    pit_Exit = interp_pit[len(interp_pit) - 1]
    smoothed_Track = smoothPoints(interp_track)
    smoothed_Pit = smoothPoints(interp_pit,mode='interp')

    return smoothed_Track, smoothed_Pit, referencePos, maxPos

def ExportPointsToCSV(file,points):
    with open(file + ".csv",'w') as f:
        f.write("NAME,LAT,LON\n")
        for point in points:
            p = list(map(str,point))
            f.write(','.join(p) + "\n")

def addPitAttchmentPoints(track,pit,pitEntrance,pitExit):
    #Manually define the trackpoint that leads to the pit
    track_dict = {x[0]: [x[1],x[2]] for x in track}
    entrance = 0
    exit = 0
    if str(pitEntrance) in track_dict:
        entrance = track_dict[str(pitEntrance)]
        print(entrance)
    else:
        print("Entrance Point Name Not Found")
        return None
    if str(pitExit) in track_dict:
        exit = track_dict[str(pitExit)]
        print(exit)
    else:
        print("Exit Point Name Not Found")
        return None
    return [[str(pitEntrance),entrance[0],entrance[1]]] + pit + [[str(pitExit),exit[0],exit[1]]] 


def normalizeKartPosition(kartPosition,MinPoint,MaxPoint):
    normalizedLAT = (float(kartPosition[0]) - float(MinPoint[0])) / ((float(MaxPoint[0]) - float(MinPoint[0])))
    normalizedLAT = 0.1 + (normalizedLAT * 0.8)
        
    normalizedLON = 1 - ((float(kartPosition[1]) - float(MinPoint[1])) / ((float(MaxPoint[1]) - float(MinPoint[1]))))
    normalizedLON = 0.1 + (normalizedLON * 0.8)

    return [normalizedLAT,normalizedLON]


def interpolatePoints(Points,numberPoints=None, spacing=None):
    #If the points list doesnt contain enough points just return the current list 
    if len(Points) < 2:
        return Points

    lats = np.array([float(p[1]) for p in Points])
    lons = np.array([float(p[2]) for p in Points])

    distances = np.zeros(len(Points))
    for i in range(1, len(Points)):
        dx = lons[i] - lons[i - 1]
        dy = lats[i] - lats[i - 1]
        distances[i] = distances[i - 1] + np.sqrt(dx**2 + dy**2)

    total_distance = distances[-1]

    if numberPoints is None:
        if spacing is None:
            spacing = total_distance / 100
        numberPoints = int(total_distance / spacing) + 1

    interp_lat = interp1d(distances, lats, kind='cubic', fill_value='extrapolate')
    interp_lon = interp1d(distances, lons, kind='cubic', fill_value='extrapolate')

    new_distances = np.linspace(0, total_distance, numberPoints)

    new_lats = interp_lat(new_distances)
    new_lons = interp_lon(new_distances)

    interpolated = []
    for i, (lat, lon) in enumerate(zip(new_lats, new_lons)):
        interpolated.append([f"interp_{i}", float(lat), float(lon)])
    
    return interpolated

def smoothPoints(points, windowLength=11,polyorder=3,mode='wrap'):
    if len(points) < windowLength:
        return points
    
    lats = np.array([float(p[1]) for p in points])
    lons = np.array([float(p[2]) for p in points])

    smoothed_lats = savgol_filter(lats, windowLength, polyorder, mode=mode)
    smoothed_lons = savgol_filter(lons, windowLength, polyorder, mode=mode)
    
    # Reconstruct points
    smoothed = []
    for i, (lat, lon) in enumerate(zip(smoothed_lats, smoothed_lons)):
        smoothed.append([points[i][0], float(lat), float(lon)])
    
    return smoothed


if __name__ == "__main__":

    track, pit, min, max = ExtractKML("purduePathTest.kml")

    #track, pit = extractKMLPointsFromPathsandPolygons("PathTest.kml")

    #nt, np, minPos, MaxPos = normalizeTrackPoints(track,pit)

    #ExportPointsToCSV("TrackLINE",nt)
    #ExportPointsToCSV("PitLINE",np)

    #track,pit = extractKMLPointsFromPoints("purdueMap.kml")
    #print(track)
    #print(pit)
    #print(reference)
    #pitEntrancePoint = 24
    #pitExitPoint = 32
    #testDriverPos = [40.43788230494788, -86.94481112554759]
    #normalizedTrack, normalizedPit, minPos, maxPos = normalizeTrackPoints(track,pit)
    
    #finalPit = addPitAttchmentPoints(normalizedTrack,normalizedPit,pitEntrancePoint,pitExitPoint)

    
    #print(normalizeKartPosition(testDriverPos,minPos,maxPos))
    #ExportPointsToCSV("NonTrack",track)
    #print(normalizedPit)
    #ExportPointsToCSV("Track",normalizedTrack)
    #ExportPointsToCSV("Pit",finalPit)

    