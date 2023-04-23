import configparser
import requests
from datetime import datetime
import time

class WsprTransceiver:
	def __init__(self, bandArray = None):
		self.bandArray = bandArray
		self.radioClubAlreadyNotified = False
	#configs
	config = configparser.ConfigParser()
	config.read('config.ini')
	callSign = config.get("configurations", "callSign")

	lineNumberToKeep = 122

	#functions
	def scrapeBand(self, band=None):
		if band is None:
			URL = f"https://www.wsprnet.org/olddb?mode=html&band=all&limit=1&findcall=w8edu&findreporter=w8edu&sort=date"
		else:
			URL = f"https://www.wsprnet.org/olddb?mode=html&band={band}&limit=1&findcall=w8edu&findreporter=w8edu&sort=date"
		# Fetch the webpage using requests and save it to a temporary file
		lastPingScraped = requests.get(URL)

		# Read the raw HTML file and keep only the specified line
		lastPingScraped = lastPingScraped.text.splitlines()

		#Extract the line to keep
		lastPingScraped = lastPingScraped[self.lineNumberToKeep - 1]

		#extract the UTC time to keep
		lastPingScraped = lastPingScraped.split(";", 1)[1].split("&", 1)[0].strip()

		# Convert the timestamp to epoch time
		epochTimeLastPing = int(datetime.strptime(lastPingScraped, "%Y-%m-%d %H:%M").strftime("%s"))
		currentTime = int(time.time())

		#find time since last ping in readable format
		secondsSinceLastPing = currentTime - epochTimeLastPing
		return epochTimeLastPing, secondsSinceLastPing, lastPingScraped

	def findLastPing(self):
		if self.bandArray is None:
			return self.scrapeBand()
		else:
			epochTimeLastPing=0
			secondsSinceLastPing=0
			lastPingScraped=0
			for bandNum in self.bandArray:
				currEpochTimeLastPing, currSecondsSinceLastPing, currLastPingScraped = self.scrapeBand(bandNum)
				if currEpochTimeLastPing > epochTimeLastPing:
					epochTimeLastPing=currEpochTimeLastPing
					secondsSinceLastPing=currSecondsSinceLastPing
					lastPingScraped=currLastPingScraped

		return epochTimeLastPing, secondsSinceLastPing, lastPingScraped

	def changeNotificationStatus(self):
		self.radioClubAlreadyNotified = not self.radioClubAlreadyNotified

	def getbands(self):
		return self.bandArray

	def getNotificationStatus(self):
		return self.radioClubAlreadyNotified
