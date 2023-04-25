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

#uses pushiver to send a message to radio club, will be replaced with discord
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

#convers time in seconds to hours and mins
def secondsToTimestamp(seconds):
	hours = seconds // 3600
	minutes = (seconds // 60) % 60
	return hours, minutes

#take in a bool for if everyone was pinged over the past 6 mins!!!
def dbCheck(transceiverList, checkNextMinute=False):
	try:
		#create items to return and push to user/logs
		updatedTransceiverList = []
		messageToPush = ""
		messageToLog = ""
		currentTime = int(time.time())
		for transceiver in transceiverList:
			#find hours and minutes since last ping
			epochTimeLastPing, secondsSinceLastPing, lastPingScraped = transceiver.findLastPing()
			hoursSinceLastPing, minutesSinceLastPing = secondsToTimestamp(secondsSinceLastPing)
			#check if there is an outage
			if maxPingTimeDiff <= secondsSinceLastPing:
				#log a outage, set time until outage reping
				messageToLog += logSystemDown.format(str(transceiver.getBands())) + "\n"
				#notify radio club if radio club was not notified yet
				if not transceiver.getNotificationStatus():
					messageToLog += logRadioClubPushedOutage.format(str(transceiver.getBands())) + "\n"
					#append string to push
					messageToPush += outageNotif.format(str(transceiver.getBands()), hoursSinceLastPing, minutesSinceLastPing) + "\n"
					transceiver.changeNotificationStatus()
			else:
				#log everything is working if it does work, set time until reping
				secondsUntilNextCheck = maxPingTimeDiff + epochTimeLastPing - currentTime + 1
				hoursUntilNextCheck, minutesUntilNextCheck = secondsToTimestamp(secondsUntilNextCheck)
				messageToLog += logSystemOnline.format(str(transceiver.getBands())) +"\n"
				if transceiver.getNotificationStatus():
					transceiver.changeNotificationStatus()
					messageToLog += logReconnect.format(str(transceiver.getBands())) + "\n"
					#append message to push:
					messageToPush += reconnectNotif.format(str(transceiver.getBands())) + "\n"
			updatedTransceiverList.append(transceiver)
			messageToLog += logLastTransmission.format(str(transceiver.getBands()), lastPingScraped, hoursSinceLastPing, minutesSinceLastPing) + "\n"
		#log all updates
		logging.info(messageToLog)
		#push messages to user if string is not blank
		if messageToPush != "":
			sendMessageToRadio(messageToPush)
		#set cron job for next minute if asked
		if checkNextMinute:
			nextMinute = datetime.now() + timedelta(minutes=1)
			nextMinuteStart = nextMinute.replace(second=0, microsecond=0)
			scheduler.add_job(dbCheck, trigger='date', run_date=nextMinuteStart, args=[updatedTransceiverList, True])
		return updatedTransceiverList

	except Exception as e:
		logging.error("Exception occurred:", exc_info=True)

if __name__ == "__main__":
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

	#log a start
	logging.critical(logStart)
	#add cron jobs for each transceiver to check in the next minute and start scheduling
	#nextMinute = datetime.now() + timedelta(minutes=1)
	#nextMinuteStart = nextMinute.replace(second=0, microsecond=0)
	#scheduler.add_job(dbCheck, trigger='date', run_date=nextMinuteStart, args=[transceiverList, True])
	dbCheck(transceiverList, True)
	scheduler.start()
