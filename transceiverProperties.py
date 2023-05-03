import configparser
import requests
import datetime
from datetime import datetime, timedelta
import time
import pandas as pd
import matplotlib.pyplot as plt


class WsprTransceiver:
	def __init__(self, bandArray = None):
		self.bandArray = bandArray
		self.radioClubAlreadyNotified = False
		#configs
		config = configparser.ConfigParser()
		config.read('config.ini')
		self.callSign = config.get("configurations", "callSign")
		self.URL = config.get("configurations", "URL")
		self.lineNumberToKeep = 122
		self.dfXAxis = config.get("configurations", "dfXAxis")
		self.dfYAxis = config.get("configurations", "dfYAxis")
		#create dataframe for tracking
		self.outageData = pd.DataFrame(columns=[self.dfXAxis, self.dfYAxis])

	#functions
	#finds last ping of band using web scraping
	#leave band blank for scraping all bands under the callsign specified in configurations.
	#output: epoch time of last ping, time since then, last ping scraped in UTC as a string
	def scrapeBand(self, band=None):
		#scrape all bands if no band was speified, or the band passed in the parameters
		if band is None:
			URLToScrape = self.URL.format("all", self.callSign, self.callSign)
		else:
			URLToScrape = self.URL.format(band, self.callSign, self.callSign)
		# Fetch the webpage using requests and save it to a temporary file
		lastPingScraped = requests.get(URLToScrape)
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

	#finds the last ping of all bands in bandArray
	#output: epoch time since last ping, seconds since last ping, last ping data scraped in UTC for any transceiver
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

	#used to determine if radio club should be pinged about an outage or reconnect.
	def changeNotificationStatus(self):
		self.radioClubAlreadyNotified = not self.radioClubAlreadyNotified
	#returns notification status.
	def getNotificationStatus(self):
		return self.radioClubAlreadyNotified
	#returns band array for logging/message purposes
	def getBands(self):
		return self.bandArray
	#logs if system was up during a given timestamp using a boolean input
	def logUptime(self, timeStamp, wsprIsUp):
		#round to nearest second
		timeStamp = timeStamp + timedelta(seconds=0) - timedelta(microseconds=timeStamp.microsecond)
		newRow = pd.DataFrame({self.dfXAxis: [timeStamp], self.dfYAxis: [wsprIsUp]})
		self.outageData = pd.concat([self.outageData, newRow], ignore_index=True)
	#returns outageData dataframe
	def getUptimeHistory(self):
		return self.outageData
