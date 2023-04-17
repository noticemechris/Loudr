#sets the maximum acceptable time threshold between pings in seconds. Set much lower when doing demonstrations
maxPingTimeDiff=7320

#in the event of an outage, sets the time interval that it will re-ping the website and see if new data was uploaded. In this case, I'm setting it to 2 mins since each data transmission takes 2 minutes
timeUntilOutageRePing=120

# URL of the webpage to scrape
URL="https://www.wsprnet.org/olddb?mode=html&band=40&limit=1&findcall=w8edu&findreporter=&sort=date"

# Webscraping code needs to delete all lines except for one of them in the scraped webpage. Below is line number to keep.
lineNumberToKeep=122

#stores time of last upload to the datbase in the file below for debugging
scrapedFile="scraped.txt"

#name to save the raw html file as for web scraing
rawHtmlFile="raw.html"

#log file name
logFile="log.log"

#api key for push notifications
token=a7f3d5m83zqsd318t3sak5x2udb428

#user key for push notifications. If needed one can create a group key that replaces the user key for the location to push to
user=uthw8zjwymiryizeazdgv9ohaifs44

#message to user in the event of an outage. Saved in txt file for ease of editing and viewing
outageNotif=$(cat outageMessage.txt)

#message to user in the event of a reconnect
reconnectNotif=$(cat reconnectMessage.txt)

#boolean if radio club is already notified of an outage or reconnect
radioClubAlreadyNotified=false

#function to notify radio club of outage or reconnect
sendMessageToRadio () {
	curl -s \
		--form-string "token=$token" \
		--form-string "user=$user" \
		--form-string "message=$1" \
		https://api.pushover.net/1/messages.json >> $logFile
}

#logs that Loudr is started up on startup
echo "STARTING LOUDR" >> $logFile

#sleep until the 2 minute mark
sleep $((120 - $(date +%s) % 120))

#readable current time for logging. ALL TIMES ARE IN UTC PER RADIO BEST PRACTICES
currentTimeReadable=$(date -u +"%Y-%m-%d %H:%M")

#script that continuously runs once startup is complete
while true
do
	#WEB SCRAPING CODE STARTS BELOW

	# Fetch the webpage using curl and save it to a temporary file
	curl -s "$URL" > "$rawHtmlFile"

	# Delete everything except for the time of the last successful upload. Saves to txt file.
	sed -n "${lineNumberToKeep}p" "$rawHtmlFile" > "$scrapedFile"
	sed -i 's/^[^;]*;//; s/&.*$//' "$scrapedFile"

	# Puts the time in Epoch time
	timeStampLastPing=$(cat "$scrapedFile")
	epochTimeLastPing=$(date -u -d "$timeStampLastPing" +"%s")
	echo "$epochTimeLastPing" >> "$scrapedFile"

	#delete the raw html file
	rm $rawHtmlFile

	#WEB SCRAPING CODE IS OVER. TIME PROCESSING STARTS BELOW

	#gets the current time in epoch time
	currentTime=$(date +%s)

	#gets the current time in a readable format
	currentTimeReadable=$(date -u +"%Y-%m-%d %H:%M")

	#finds the time in seconds before the last ping
	secondsSinceLastPing=$((currentTime - epochTimeLastPing))

        # Calculate the hours and minutes since last ping for ease of reading
        hoursSinceLastPing=$(( secondsSinceLastPing / 3600 ))
        minutesSinceLastPing=$(( ( secondsSinceLastPing / 60 ) % 60 ))

	#POSSIBLE ACTIONS BASED ON TIME OF LAST PING AND CURRENT TIME START BELOW

	#verifies that the time since last ping is smaller than the threshold. If the time since last ping is above the threshold, and the user was not already notified, it sends a push notification
	if [[ "$maxPingTimeDiff" -lt "$secondsSinceLastPing" ]]; then
		echo "$currentTimeReadable : Wspr is not wspring." >> $logFile

		#uncomment the line below to cause chaos
		#wall URGENT MESSAGE: RADIO ANTENNAS BLEW OFF THE ROOF OF GLENNAN. ATTEMPTING TO RECONNECT TO MONITORING SYSTEM

		#sets the seconds until the next check happens.
		secondsUntilNextCheck=$timeUntilOutageRePing

		#notifies radio club of outage if radio club was not already notified
		if ! $radioClubAlreadyNotified; then
			echo "$currentTimeReadable : Notifying radio club system is offline" >> $logFile
			messageToPush=${outageNotif//\$hoursSinceLastPing/$hoursSinceLastPing}
			messageToPush=${messageToPush//\$minutesSinceLastPing/$minutesSinceLastPing}
			sendMessageToRadio "$messageToPush"
			radioClubAlreadyNotified=true
		fi
	else
		#In the event everything is still working, logs it and checks again at the time of the last ping + the threshold + 1 to prevent redundancies
		secondsUntilNextCheck=$((maxPingTimeDiff + epochTimeLastPing - currentTime + 1))
        	hoursUntilNextCheck=$(( secondsUntilNextCheck / 3600 ))
        	minutesUntilNextCheck=$(( (secondsUntilNextCheck / 60 ) % 60 ))
                echo "$currentTimeReadable : Wspr is wspring, will test it again in $hoursUntilNextCheck hours: $minutesUntilNextCheck minutes." >> $logFile
		#notifies radio club systm is back online ifneeded
		if $radioClubAlreadyNotified; then
			messageToPush=$reconnectNotif
			sendMessageToRadio "$messageToPush"
			radioClubAlreadyNotified=false
			echo "$currentTimeReadable : Radio club notified system is back online." >> $logFile
		fi
	fi

	#logs the last ping
	echo "$currentTimeReadable : Last data transmission to the server was $timeStampLastPing UTC. The time since last transmission is $hoursSinceLastPing hours: $minutesSinceLastPing minutes." >> $logFile

	#sleep unti it has to check again, determined above
	sleep $secondsUntilNextCheck
done
