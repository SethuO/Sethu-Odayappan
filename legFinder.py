#Automating district location based off of individual's addresses

#Each district is stored as a polygon with thousands of edges
#We can extract the points that make up the polygon
#We can use these to determine whether or not a coordinate is in a district

#Importing Libraries
import shapefile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pyproj
from geopy.geocoders import Nominatim
import time

t = time.time()

#Loop to extract [x,y] file of all points for one senate district
def shpLoop(j):
    
    #Loading object for district #J
    feature = sf.shapeRecords()[j]
    first = feature.shape.__geo_interface__

    #Converting to array
    data = np.asarray(first["coordinates"])

    #Empty data structures to fill with coordinates of each polygon point
    x = np.array([])
    y = np.array([])

    #Three different types of data structures
    #Normalizing through try/except statements
    #Appending coordinates of polygon points into x and y array
    try:
        for i in range (np.size(data[0][0], axis=0)):
            x = np.append([x],data[0][0][i][0])
            y = np.append([y],data[0][0][i][1])

    except:
        try:
            for i in range (np.size(data, axis=1)):
                x = np.append([x],data[:,i][0][0])
                y = np.append([y],data[:,i][0][1])
                
        except:
            for i in range (np.size(data[0], axis=0)):
                x = np.append([x],data[0][i][0])
                y = np.append([y],data[0][i][1])

    return (x,y)

#Finding the number of points that make up each district's defining polygon
def lengthFinder(numDistricts):

    #Preallocating vector
    maxLengths = np.zeros(numDistricts)

    #Looping through all districts and counting number of points
    for j in range(numDistricts):
        (x,y) = shpLoop(j)
        maxLengths[j] = len(x)

    #Removing extraneous ends and returning length    
    return(sum(maxLengths)-39)

#Extracting data in a structure for the polygon locating algorithm
#Matrix for statewide polygon vertices with [x1,x2,y1,y2,district] for rows
def dataExtract(numDistricts, length):

    #Preallocating arrays
    maxLengths = np.zeros(numDistricts)
    df = np.zeros([length,5])
    prevInd = 0

    #Looping to find (x,y) for each district
    for j in range(numDistricts):
        (x,y) = shpLoop(j)

        #For the current range within all districts
        for k in range(prevInd,prevInd+len(x)-1):

            #For all but endpoints, assigning [x1,x2,y1,y2,district]
            df[k] = np.array([x[k-prevInd], x[k-prevInd+1], y[k-prevInd], y[k-prevInd+1],j])

        #Assigning for endpoint
        df[k+1] = np.array([x[len(x)-1], x[0], y[len(x)-1], y[0], j])

        #Increasing position index
        prevInd = k+1

    return(df)


#Algorithm to determine which polygon the point is inside of
def algorithm(data, meters):
    
    #Empty vector with a scalar for each district
    #NOTE: Sorry for the inconsistencies, the 40 should be districtNum
    crosses = np.zeros(40)

    #For each polygon vertex in the state
    for i in range(len(data)):

        #Find all the edges where our points y value is inside their range
        if data[i,0] > meters[0] or data[i,1] > meters[0]:

            #Find if either vertex is to the right of the point
            if data[i,2] < meters[1] and data[i,3] > meters[1] or data[i,2] > meters[1] and data[i,3] < meters[1]:

                #If so, find if the point is to the left of the slope  
                slope = (data[i,3]-data[i,2])/(data[i,1]-data[i,0])

                #For positive slopes, point is left of edge if above it
                if slope >= 0:
                    if y > slope*(meters[0]-data[i,0])+data[i,2]:
                        crosses[int(data[i,4])] = crosses[int(data[i,4])]+1

                #For negative slopes, point is left of edge if below it
                if slope <= 0:
                    if y < slope*(meters[0]-data[i,0])+data[i,2]:
                        crosses[int(data[i,4])] = crosses[int(data[i,4])]+1
                          
    #If crosses are odd we're in that district!
    #Returns a boolean array for crosses.
    if sum(crosses%2)==1:
        return crosses%2
    
    #If not something went wrong!
    #Return crosses vector for analysis
    else:
        return crosses

#Normalizing street names to ensure proper geolocation
def checkAdd(street):
    #Universalizing to lower case
    adNormal = street.lower()

    #Stopwords and list of letters
    stopwords = ["st","street","rd","road","lane","ln","ave","avenue","circle","cir","court","ct","plaza","plz","alley","aly","terrace","ter"]
    alphabet = "abcdefghijklmnopqrstuvwxyz"

    #Looping through each stopword
    for i in range(len(stopwords)):

        #If there is a stopword in the address
        if stopwords[i] in adNormal:

            #Index the location
            ind = adNormal.index(stopwords[i])
            
            #Check to see if it's a part of the name
            try:
                if adNormal[ind-1] or adNormal[ind+1] in alphabet:
                    ind = adNormal.index(stopwords[i],ind+1)
            except:
                ind = ind

            #Cut the street name so it ends after the suffix
            ind = ind + len(stopwords[i])
            realAdd = adNormal[:ind]

            return realAdd
            
#Getting coordinates from address   
def coordLookup(street,city,state,postalcode):

    #Creating dict of address
    address = dict({"street":str(street), "city":str(city), "state":str(state), "postalcode":str(postalcode)})

    #Running through Nominatim's API
    geolocator = Nominatim(user_agent = "My Application")
    location = geolocator.geocode(address)
    
    #Coords stored as tuple
    coordinates = location[1]
    return coordinates

#Converting from coordinates to LCC using inputted data from .prj file
p = pyproj.Proj(proj='lcc',lat_1 = 41.71666666, lat_2=42.68333,lon_0=-71.5,x_0=200000,y_0=750000, lat_0=41)
def converter(lat,long):
    return p(long,lat)


#----------------------------------------------------------------------
#START OF FUNCTION CALLING!
#Processing data... Runtime = 15 seconds
#----------------------------------------------------------------------

#Reading Data from .shp file
#NOTE: THIS IS MY DATA PATH IT MUST BE ADJUSTED
sf = shapefile.Reader("/Users/justi/OneDrive/Documents/datasets/OCPF Data/senate2012/SENATE2012_POLY.shp")

#Finding the amount of vertices for each district
length = int(lengthFinder(40))
#Extracting district data for algorithm
df = dataExtract(40,length)

#Preallocating districts vector and failure cases
reps = np.array([])
diverged = np.array([])
badAddress = np.array([])
outOfState = np.array([])

#Loading CSV Data and reorganizing data structures
#NOTE: DON'T FORGET ABOUT THE DATA PATH
names = pd.read_excel("Senate Full Contribution Data.xlsx")
names = names.to_numpy()

#Converting zipcodes to 5-digit strings (2048-->"02048")
#Needed for geolocating
for i in range(len(names)):
    if type(names[i][6])!=str:
        names[i][6]=str(names[i][6])
        if len(names[i][6])!=5:
            names[i][6] = "0"+names[i][6]

#Deleting PO Boxes and Apt numbers which invalidate geolocation
for i in range(len(names)):
    try:
        temp = checkAdd(names[i][3])
        if type(temp) == str:
            names[i][3] = temp
    except:
        continue
#----------------------------------------------------------------------
#Indicating start of heavy loop
print("loaded")

#Loop through csv of people
for i in range(len(names)):
    t=time.time()
    #Adding time to comply with api 1 request per second rule
    time.sleep(0.75)

    #Find coordinates from address and check to see it's in state
    #Exception handler for invalid adresses
    try:
        lat,long = coordLookup(names[i][3],names[i][4],names[i][5],names[i][6])
        #Check for out of state only if address is valid
        if names[i][5]!="MA":
            outOfState = np.append(outOfState, [i])
            continue

    except:
        #If geolocation fails, adress is invalid
        badAddress = np.append(badAddress,[i])
        #print("bad address")
        continue

    #Converting latitude longitude to the custom LCC projection used for MA
    x,y = converter(lat,long)
    meters = np.array([x,y])

    #Run polygon location algorithm
    district = algorithm(df,meters)

    #If it returns boolean array with only 1 true, assign that as our district
    if sum(district)==1:
        reps=np.append(reps,[np.argmax(district)])
        #print(np.argmax(district))
    #If not, assume that the polygon location test diverged/failed
    else:
        diverged=np.append(diverged,[i])
        #print("diverged")
    #print(time.time()-t)
    if i%1000 == 0:
        print(i)
        print(time.time()-t)
    
#Analyzing test        
print(reps)
print(outOfState)
print(diverged)
print(badAddress)
#----------------------------------------------------------------------
#End of File
