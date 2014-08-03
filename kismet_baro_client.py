#!/usr/bin/python
import csv
import re
import telnetlib
from Adafruit_BMP085 import BMP085
import os
import getopt
import sys

gps_fields = ['lat','lon','fix']
network_fields = ['bssid','type','ssid','rssi']

def format_coords(coord_string):
	#Turn the Kismet "*GPS: " string into a coords dictionary
	coords = {}
	params = coord_string.split(' ')
	for idx,param in enumerate(gps_fields):
		coords[param]=str(params[idx+1])
	return coords
		
def format_network(network_string):
	#Turn the Kismet "*NETWORK: " string into a network dictionary
	#Strip the /0x01 out, which Kismet uses for quoting the SSID name
	network = {}
	network_string = ''.join(i for i in network_string if ord(i)<128 and ord(i)>1)	
	params = network_string.split(' ')
	for idx,param in enumerate(network_fields):
		network[param]=str(params[idx+1])
	return network	
		
def log_network_sighting(network, coords, alt, csv_writer):
	#Write the network & coordinates to the CSV
	csvdict = dict(network.items() + coords.items())
	csvdict['alt'] = alt
	csv_writer.writerow(csvdict)

def usage():
	print "kismet_barometer_client"
	print "\t-h - Help"
	print "\t-s <Kismet Server IP>"
	print "\t\tDefault 127.0.0.1"
	print "\t-p <kismet Server Port>"
	print "\t\tDefault 2501"
	print "\t-o <Output file>"
	print "\t\tRequired"
	print "\t-i <Input file>"
	print "\t-k  - Generate KML"
	print "\n"
	print "Example Usage:"
	print "./kismet_barometer_client -s 127.0.0.1 -p 2501 -o outputfile.kmz"


def main(argv):
	#Ensure it's running as root.
	#This is required in order to access the I2C bus.
	if os.geteuid() != 0:
    		print("Accessing the Barometer on the I2C bus requires root privileges.")
		print("Run this again as root")
		return

	#Parse out the arguments
	try:
		opts, args = getopt.getopt(sys.argv[1:],"hs:p:o:i:k:")
	except getopt.GetoptError as err:
		print str(err)
		usage()
		sys.exit()
	
	#Defaults
	server = "127.0.0.1"
	port = "2501"
	output_filename = ""
	input_file = ""
	generate_kml = False
	
	for o, a in opts:
		if o == "-h":
			usage()
			return
		elif o == "-s":
			server = a
		elif o == "-p":
			port = a
		elif o == "-o":
			output_filename = a
		elif o == "-i":
			input_file = a
		elif o == "-k":
			generate_kml = True		


	if output_filename == "":
		print "Missing -o parameter"
		usage()
		return 

	try:
		outfile = open(output_filename,"wb")
	except:
		print "Unable to create/open file: %s" % output_filename
	
	fieldnames = gps_fields[:] + network_fields[:]
	fieldnames.append("alt")
	writer = csv.DictWriter(outfile,fieldnames)
	writer.writeheader()

	try:
		print "Attempting to connect to BMP085 on I2C bus"	
		bmp = BMP085(0x77)
		start_alt = bmp.readAltitude()
		print "Success:  Starting altitude set to %s" % start_alt
	except:
		print "ERROR: Unable to connect to Barometer."
		print "Ensure that that the barometer is correctly connected to the I2C Bus."
		return

	#Kismet client setup & selecting output options
	try:
		print "Connecting to Kismet at %s:%s"%(server,port)
		kismet_client = telnetlib.Telnet(server, port)
	except:
		print "ERROR: Connection to Kismet Server failed"
		print "Ensure Kismet is running, and this host is in the kismet.conf 'allowedhosts' line"
		return

	print "Setting up Kismet options"
	kismet_client.write("\n")
	#Enabling Network & GPS sentances from Kismet
	kismet_client.write("!0 ENABLE NETWORK %s\n" % ",".join(network_fields))
	kismet_client.write("!0 ENABLE GPS %s\n" % ",".join(gps_fields))

	coords = {}
	start_time = 0
	time = 0
	
	while True:
		kismet_string = kismet_client.read_until("\n");

		if "*TIME: " in kismet_string:
			if start_time == 0:
				start_time = int(kismet_string.split(' ')[1])
				time = int(kismet_string.split(' ')[1])
			else:
				time = int(kismet_string.split(' ')[1])

		elif "*KISMET: " in kismet_string:
			print "Received Kismet Server Info"
			print kismet_string
			
		elif (time-start_time)<2:
			#Kismet sends the entire history of networks as a big block of *NETWORK sentances in the first few seconds.
			#As the current GPS coordintes don't reflect the recorded RSSI, we ignore these.
			pass
		
		elif "*NETWORK: " in kismet_string:
			net = format_network(kismet_string)
			log_network_sighting(net, coords, bmp.readAltitude(), writer)
			#Flush & Sync the CSV.
			#This is useful if the script is improperly closed, ie. loses power.
			outfile.flush()
			os.fsync(outfile)
			
		elif "*GPS" in kismet_string and kismet_string.split(' ')[3]:
			coords = format_coords(kismet_string)
			
		elif "*PROTOCOLS: " in kismet_string:
			#Protocols message from KISMET
			pass
		
		else:
			print "WTF kind of sentance am I dealing with here: %s" % kismet_string
		

if __name__ == "__main__":
	main(sys.argv[1:])
