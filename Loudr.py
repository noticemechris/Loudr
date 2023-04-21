import os
import re
import time
import requests
import datetime
import logging
import http.client
import urllib
import configparser
import schedule
from datetime import datetime, timedelta

# Configurations, now replaced as a conf file!
config = configparser.ConfigParser()
config.read('config.ini')
maxPingTimeDiff = int(config.get("configurations", "maxPingTimeDiff"))
timeUntilOutageRePing = int(config.get("configurations", "timeUntilOutageRePing"))
logFile = config.get("configurations", "logFile")
twoMinutes = 120

#Strings for logging
logMessageSent = config.get("logs", "logMessageSent")
logStart = config.get("logs", "logStart")
logSystemDown = config.get("logs", "logSystemDown")
logRadioClubPushedOutage = config.get("logs", "logRadioClubPushedOutage")
logSystemOnline =  config.get("logs", "logSystemOnline")
logReconnect = config.get("logs", "logReconnect")
logLastTransmission = config.get("logs", "logLastTransmission")

#Paths of strings for push notifications
outageNotifPath = config.get("notifs", "outageNotifPath")
reconnectNotifPath = config.get("notifs", "reconnectNotifPath")

#web scraping info, to be updated when adding support for other transceivers, etc
URL = "https://www.wsprnet.org/olddb?mode=html&band=40&limit=1&findcall=w8edu&findreporter=w8edu&sort=date"
lineNumberToKeep = 122

#secret stuff
token = os.environ["pushoverApiKey"]
user = os.environ["pushoverUser"]

#import messages to users as strings
with open(outageNotifPath, "r") as f:
	outageNotif = f.read()
with open(reconnectNotifPath, "r") as f:
	reconnectNotif = f.read()

#set up internal logger
logging.basicConfig(
	level=logging.INFO,  # Log messages with level INFO or higher
	format='%(asctime)s - %(levelname)s - %(message)s',  # Format of log messages
	handlers=[logging.FileHandler(logFile)]  # Log messages to a file called 'log.log'
)

radioClubAlreadyNotified = False

def sendMessageToRadio(message):
	conn = http.client.HTTPSConnection("api.pushover.net:443")
	conn.request("POST", "/1/messages.json",
		urllib.parse.urlencode({
			"token": token,
			"user": user,
			"message": message,
		}), { "Content-type": "application/x-www-form-urlencoded" })
	conn.getresponse()
	logging.critical(logMessageSent.format(message))

def scrapeLastPing():
    # Fetch the webpage using requests and save it to a temporary file
    lastPingScraped = requests.get(URL)

    # Read the raw HTML file and keep only the specified line
    lastPingScraped = lastPingScraped.text.splitlines()

    #Extract the line to keep
    lastPingScraped = lastPingScraped[lineNumberToKeep - 1]

    #extract the UTC time to keep
    lastPingScraped = lastPingScraped.split(";", 1)[1].split("&", 1)[0].strip()

    # Convert the timestamp to epoch time
    epochTimeLastPing = int(datetime.strptime(lastPingScraped, "%Y-%m-%d %H:%M").strftime("%s"))
    currentTime = int(time.time())

    #find time since last ping in readable format
    secondsSinceLastPing = currentTime - epochTimeLastPing
    return epochTimeLastPing, secondsSinceLastPing, lastPingScraped

def secondsToTimestamp(seconds):
	hours = seconds // 3600
	minutes = (seconds // 60) % 60
	return hours, minutes

def dbCheck():
	#define global variables
	global radioClubAlreadyNotified

	currentTime = int(time.time())

	#scrape wsprnet for the time of last ping
	epochTimeLastPing, secondsSinceLastPing, lastPingScraped = scrapeLastPing()

	#find hours and minutes since last ping
	hoursSinceLastPing, minutesSinceLastPing = secondsToTimestamp(secondsSinceLastPing)

	#check if there is an outage
	if maxPingTimeDiff < secondsSinceLastPing:
		#log a outage, set time until outage repin
		logging.info(logSystemDown)

		#notify radio club if radio club was not notified yet
		if not radioClubAlreadyNotified:
			logging.info(logRadioClubPushedOutage)
			messageToPush = outageNotif.format(hoursSinceLastPing, minutesSinceLastPing)
			sendMessageToRadio(messageToPush)
			radioClubAlreadyNotified = True
	else:
		#log everything is working if it does work, set time until reping
		secondsUntilNextCheck = maxPingTimeDiff + epochTimeLastPing - currentTime + 1
		hoursUntilNextCheck, minutesUntilNextCheck = secondsToTimestamp(secondsUntilNextCheck)
		logging.info(logSystemOnline)

		#send message if system is back online after an outage
		if radioClubAlreadyNotified:
			messageToPush = reconnectNotif
			sendMessageToRadio(messageToPush)
			radioClubAlreadyNotified = False
			logging.info(logReconnect)

	logging.info(logLastTransmission.format(lastPingScraped, hoursSinceLastPing, minutesSinceLastPing))


# Find the next multiple of two minutes
#nextMultipleOfTwo = now + timedelta(minutes=((now.minute // 2 + 1) * 2 - now.minute))
#nextMultipleOfTwo = nextMultipleOfTwo.replace(second=0, microsecond=0)
#print(nextMultipleOfTwo)

#get datetime of current time
#dateTimeOfCurrentTime = datetime.fromtimestamp(time.time())
# Find the next multiple of two minutes (in epoch time)
#nextMultipleOfTwo = (time.time() // twoMinutes + 1) * twoMinutes

# Convert the next multiple of two minutes (in epoch time) to a datetime object
#startTime = datetime.fromtimestamp(nextMultipleOfTwo)

# Schedule the job to run every 2 minutes, starting at the next multiple of two minutes
#schedule.every(0.03333333333333333).hours.at(:00).do(dbCheck)

schedule.every(2).minutes.do(dbCheck)
logging.critical(logStart)
#at the top of 2 mins, start checking database and see if something was logged there
#schedule.every(2).minutes.at().do(dbCheck)
while True:
    schedule.run_pending()
    time.sleep(1)
