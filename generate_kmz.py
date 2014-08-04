#!/usr/bin/python
import csv
import re
import telnetlib
import os
import getopt
import sys
from scipy.interpolate import griddata
import numpy
import matplotlib.pyplot as plt
import simplekml
from simplekml import AltitudeMode

def usage():
	print "generate_kmz.py"
	print "\t-h - Help"
	print "\t-i <Input file>"
	print "\t\tRequired"
	print "\t-o <Output file>"
	print "\t\tDefault: <input filename>.kmz"
	print "\t-r <resolution>"
	print "\t\tDefault: 10.  Used to determine the interpolation resolution."
	print "\t\tIncreasing this may significantly increase runtime."
	print "\t-O <Altitude Offset in Meters>"
	print "\t\tDefault: 0.  This is used to determine the offset between the levels read and sea level."
	print "\tAt least ONE of the following is required:"
	print "\t-s <ssid>"
	print "\t\tSSID of Target Network"
	print "\t-b <bssid>"
	print "\t\tBSSID of Target Network (00:00:00:00:00:00)"
	#print "\t-n <slice count>"
	#Haven't gotten to this yet...
	#print "\t\tNumber of horizontal slices"
	print "Example Usage:"
	print "./generate_kmz -i flight7.csv -s bobs-linksys"
	print "./generate_kmz -i flight7.csv -o flight7_linksys.kmz -r 15 -r 20 -s bobs-linksys -b de:ad:be:ef"

def main(argv):
	input_filename = ""
	output_filename = ""
	resolution = 10
	altitude_offset = 0
	bssid = "any"
	ssid = "any"
	slice_count = 0
	try:
		opts, args = getopt.getopt(sys.argv[1:],"hi:o:r:a:b:s:n:")
	except getopt.GetoptError as err:
		print str(err)
		usage()
		sys.exit()

	for o, a in opts:
		if o == "-h":
			usage()
			return
		elif o == "-i":
			input_filename = a
		elif o == "-r":
			resolution = int(a)
		elif o == "-o":
			output_filename = a
		elif o == "-a":
			altitude_offset = int(a)
		elif o == "-b":
			bssid = str(a)
		elif o == "-s":
			ssid = str(a)
		elif o == "-n":
			slice_count = int(n)
	if input_filename is "":
		print "Must specify input file with -i"
		return
	if ssid=="" and bssid=="":
		print "Must specify either an SSID (-s) or BSSID (-b)"
		return
	
	if altitude_offset == 0:
		print "WARNING: Sanity Check: No Altitude Offset.  Starting at sea-level"
	
	if output_filename == "":
		output_filename = input_filename + ".kmz"
			
	print "Filtering on SSID = %s and BSSID = %s"%(ssid,bssid)
	
	x = []
	y = []
	z = []
	v = []
	try:
		input = open(input_filename)
		print "Reading data from %s" % input_filename
	except:
		print "ERROR: Unable to read %s" % input_filename
		return
		
	reader = csv.DictReader(input)
	datapoint_count = 0
	for row in reader:
		if (ssid=="any" and row['bssid']== bssid) or (bssid=="any" and row['ssid']==ssid) or (bssid==row['bssid'] and ssid==row['ssid']):
			x.append(float(row['lon']))
			y.append(float(row['lat']))
			z.append(float(row['alt']))
			v.append(float(row['rssi']))
			datapoint_count = datapoint_count+1
	print "Identified %s relevant data points" % datapoint_count
	
	#The range of each axis desired
	xr = numpy.linspace(min(x),max(x),resolution)
	yr = numpy.linspace(min(y),max(y),resolution)
	zr = numpy.linspace(min(z),max(z),resolution)
	
	x_slice,y_slice = numpy.meshgrid(xr,yr)
	
	print "Performing Interpolation"
	#The expaded coordinates of each axis across the grid.
	[xi,yi,zi] = numpy.meshgrid(xr,yr,zr)	
	vi = griddata((x,y,z),v,(xi,yi,zi),method='linear',fill_value=min(v))
	
	figures = []
	slice_num = 0
	for idx in range(0,resolution):
		if idx%10 == 0: print "Generating slice %s of %s" % (idx,resolution)
		
		plt.figure()
		alt = zi[0][0][idx]
		CS = plt.contour(x_slice,y_slice,vi[idx],linewidths=3)
		plt.clabel(CS, inline=1, fontsize=10)
		t = plt.title(str(int(alt))+"m")
		t.set_color("red")
		t.set_weight("bold")
		plt.axis('off')
		figname = 'alt_%s.png'%idx
		plt.savefig(figname,transparent=True)
		figures.append({'figname':figname,'alt':alt+altitude_offset})
		plt.close()
		
	print "Interpolation complete.  Writing KMZ"
	
	kml = simplekml.Kml()
	for fig in figures:
		image_inkmz = kml.addfile(fig['figname'])
		overlay = kml.newgroundoverlay(name=fig['figname'],altitude=fig['alt'],altitudemode=AltitudeMode.absolute)
		overlay.icon.href=image_inkmz
		overlay.latlonbox.north = max(xr)
		overlay.latlonbox.south = min(xr)
		overlay.latlonbox.east = max(yr)
		overlay.latlonbox.west = min(yr)

	kml.savekmz(output_filename)
	for fig in figures:
		os.remove(fig['figname'])
	
	print "KMZ written to %s" % output_filename
		
if __name__ == "__main__":
	main(sys.argv[1:])
