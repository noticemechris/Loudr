import os
import re
import time
import requests
import datetime
import logging
import http.client
import urllib
import configparser
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
import warnings
import pytz
import transceiverProperties
warnings.filterwarnings("ignore", message="The localize method is no longer necessary")


# Configurations, now replaced as a conf file!
config = configparser.ConfigParser()
config.read('config.ini')
maxPingTimeDiff = int(config.get("configurations", "maxPingTimeDiff"))
timeUntilOutageRePing = int(config.get("configurations", "timeUntilOutageRePing"))
logFile = config.get("configurations", "logFile")
transceiverBandList = [list(map(int, array.split(','))) for array in config.get("configurations", "transceiverBandList").split(';')]

#Strings for logging
logMessageSent = config.get("logs", "logMessageSent")
logStart = config.get("logs", "logStart")
logSystemDown = config.get("logs", "logSystemDown")
logRadioClubPushedOutage = config.get("logs", "logRadioClubPushedOutage")
logSystemOnline =  config.get("logs", "logSystemOnline")
logReconnect = config.get("logs", "logReconnect")
logLastTransmission = config.get("logs", "logLastTransmission")
logCreateTransceivers = config.get("logs", "logCreateTransceivers")

#Paths of strings for push notifications
outageNotifPath = config.get("notifs", "outageNotifPath")
reconnectNotifPath = config.get("notifs", "reconnectNotifPath")

#secret stuff hidden in ~/.bashrc
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
logging.getLogger('apscheduler').setLevel(logging.CRITICAL)

#set up a list of Transceivers using the band list
transceiverList = []
for transceiver in transceiverBandList:
	transceiverList.append(transceiverProperties.WsprTransceiver(transceiver))

#log all reated transceivers
logging.critical(logCreateTransceivers.format(str(transceiverBandList)))

#create scheduler
scheduler = BlockingScheduler()

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

def secondsToTimestamp(seconds):
	hours = seconds // 3600
	minutes = (seconds // 60) % 60
	return hours, minutes

def dbCheck(transceiver, checkNextMinute=False):
	currentTime = int(time.time())
	print("ooga")
	#scrape wsprnet for the time of last ping
	epochTimeLastPing, secondsSinceLastPing, lastPingScraped = transceiver.findLastPing()
	print("booga")
	#print(str(epochTimeLastPing) + str(secondsSinceLastPing) + str(lastPingScraped))
	#find hours and minutes since last ping
	hoursSinceLastPing, minutesSinceLastPing = secondsToTimestamp(secondsSinceLastPing)

	#check if there is an outage
	if maxPingTimeDiff < secondsSinceLastPing:
		#log a outage, set time until outage repin
		logging.info(logSystemDown)

		#notify radio club if radio club was not notified yet
		if not transceiver.getNotificationStatus():
			logging.info(logRadioClubPushedOutage)
			messageToPush = outageNotif.format(hoursSinceLastPing, minutesSinceLastPing)
			sendMessageToRadio(messageToPush)
			transceiver.changeNotificationStatus()
	else:
		#log everything is working if it does work, set time until reping
		secondsUntilNextCheck = maxPingTimeDiff + epochTimeLastPing - currentTime + 1
		hoursUntilNextCheck, minutesUntilNextCheck = secondsToTimestamp(secondsUntilNextCheck)
		logging.info(logSystemOnline)

		#send message if system is back online after an outage
		if transceiver.getNotificationStatus():
			messageToPush = reconnectNotif
			sendMessageToRadio(messageToPush)
			transceiver.changeNotificationStatus()
			logging.info(logReconnect)

	logging.info(logLastTransmission.format(transceiver.getBands(), lastPingScraped, hoursSinceLastPing, minutesSinceLastPing))

	if checknextMinute:
		nextMinute = datetime.now() + timedelta(minutes=1)
		nextMinuteStart = next_minute.replace(second=0, microsecond=0)
		scheduler.add_job(dbCheck, trigger='date', run_date=nextMinuteStart, args=[transceiver, True])
	else:
		return transceiver

if __name__ == "__main__":
	#log a start
	logging.critical(logStart)
	#add cron jobs for each transceiver to check in the next minute and start scheduling
	for transceiver in transceiverList:
		nextMinute = datetime.now() + timedelta(minutes=1)
		nextMinuteStart = nextMinute.replace(second=0, microsecond=0)
		scheduler.add_job(dbCheck, trigger='date', run_date=nextMinuteStart, args=[transceiver, True])
		print("scheduled")
	scheduler.start()
