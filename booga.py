from transceiverProperties import WsprTransceiver

# Create a WsprTransceiver object with the specified bandArray
transceiver = WsprTransceiver(bandArray=[20, 30, 80])

# Call the findLastPing() method on the transceiver object
epochTimeLastPing, secondsSinceLastPing, lastPingScraped = transceiver.findLastPing()

# Print the results
print("Epoch Time of Last Ping:", epochTimeLastPing)
print("Seconds Since Last Ping:", secondsSinceLastPing)
print("Last Ping Scraped:", lastPingScraped)
