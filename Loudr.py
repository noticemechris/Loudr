import os
import re
import time
import requests
from datetime import datetime
import logging
import http.client
import urllib
import configparser


# Configurations, now replaced as a conf file!
config = configparser.ConfigParser()
config.read('config.ini')
maxPingTimeDiff = int(config.get("configurations", "maxPingTimeDiff"))
timeUntilOutageRePing = int(config.get("configurations", "timeUntilOutageRePing"))
logFile = config.get("configurations", "logFile")

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

logging.critical(logStart)

# Sleep until the 2 minute mark
time_to_sleep = (120 - int(time.time()) % 120)
time.sleep(time_to_sleep)

while True:
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
	hoursSinceLastPing = secondsSinceLastPing // 3600
	minutesSinceLastPing = (secondsSinceLastPing // 60) % 60

	#check if there is an outage
	if maxPingTimeDiff < secondsSinceLastPing:
		#log a outage, set time until outage reping
		logging.info(logSystemDown)
		secondsUntilNextCheck = timeUntilOutageRePing

		#notify radio club if radio club was not notified yet
		if not radioClubAlreadyNotified:
			logging.info(logRadioClubPushedOutage)
			messageToPush = outageNotif.format(hoursSinceLastPing, minutesSinceLastPing)
			sendMessageToRadio(messageToPush)
			radioClubAlreadyNotified = True
	else:
		#log everything is working if it does work, set time until reping
		secondsUntilNextCheck = maxPingTimeDiff + epochTimeLastPing - currentTime + 1
		hoursUntilNextCheck = secondsUntilNextCheck // 3600
		minutesUntilNextCheck = (secondsUntilNextCheck // 60) % 60
		logging.info(logSystemOnline.format(hoursUntilNextCheck, minutesUntilNextCheck))

		#send message if system is back online after an outage
		if radioClubAlreadyNotified:
			messageToPush = reconnectNotif
			sendMessageToRadio(messageToPush)
			radioClubAlreadyNotified = False
			logging.info(logReconnect)

	logging.info(logLastTransmission.format(lastPingScraped, hoursSinceLastPing, minutesSinceLastPing))
	time.sleep(secondsUntilNextCheck)
