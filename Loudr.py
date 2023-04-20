import os
import re
import time
import requests
from datetime import datetime
import logging
import http.client
import urllib

# Configurations, to bereplaces as conf file
maxPingTimeDiff = 241
timeUntilOutageRePing = 120
URL = "https://www.wsprnet.org/olddb?mode=html&band=40&limit=1&findcall=w8edu&findreporter=&sort=date"
lineNumberToKeep = 122
scrapedFile = "scraped.txt"
rawHtmlFile = "raw.html"
logFile = "log.log"
token = os.environ["pushoverApiKey"]
user = os.environ["pushoverUser"]

#import messages as strings
with open("outageMessage.txt", "r") as f:
	outageNotif = f.read()
with open("reconnectMessage.txt", "r") as f:
	reconnectNotif = f.read()

#set up internal logger
logging.basicConfig(
	level=logging.INFO,  # Log messages with level INFO or higher
	format='%(asctime)s - %(levelname)s - %(message)s',  # Format of log messages
	handlers=[logging.FileHandler('log.log')]  # Log messages to a file called 'log.log'
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
	logging.info("Pushed to user: {}".format(message))

logging.info("STARTING LOUDR")

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
		logging.critical("Wspr is not wspring.")
		secondsUntilNextCheck = timeUntilOutageRePing

		#notify radio club if radio club was not notified yet
		if not radioClubAlreadyNotified:
			logging.info("Notifying radio club system is offline")
			messageToPush = outageNotif.format(hoursSinceLastPing, minutesSinceLastPing)
			sendMessageToRadio(messageToPush)
			radioClubAlreadyNotified = True
	else:
		#log everything is working if it does work, set time until reping
		secondsUntilNextCheck = maxPingTimeDiff + epochTimeLastPing - currentTime + 1
		hoursUntilNextCheck = secondsUntilNextCheck // 3600
		minutesUntilNextCheck = (secondsUntilNextCheck // 60) % 60
		logging.info(f"Wspr is wspring, will test it again in {hoursUntilNextCheck} hours: {minutesUntilNextCheck} minutes.")

		#send message if system is back online after an outage
		if radioClubAlreadyNotified:
			messageToPush = reconnectNotif
			sendMessageToRadio(messageToPush)
			radioClubAlreadyNotified = False
			logging.info("Radio club notified system is back online.")

	logging.info(f"Last data transmission to the server was {lastPingScraped} UTC. The time since last transmission is {hoursSinceLastPing} hours: {minutesSinceLastPing} minutes.")
	time.sleep(secondsUntilNextCheck)
