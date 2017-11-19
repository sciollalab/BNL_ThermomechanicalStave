#---------------------------------------------
# Processes images of strips for the
# ATLAS inner tracker stave core assembly
#
# June 16, 2017
# Catherine Nicoloff
#---------------------------------------------

import numpy as np
import scipy as sp
import matplotlib.pyplot as plt
import cv2
import os
import sys
import re
import csv

#---------------------------------------------
# Check if the ROI is inside the edges of the 
# image
#---------------------------------------------	
def check_ROI(loc, rect, w, h):
	# keep our roi off the exact edge of the image
	offset = 10

	right = loc[0]+int(rect[1]/2)
	if (right >= w-offset):
		right = w-offset-1
	left = right-rect[1]
	if (left < 0):
		left = offset
	bottom = loc[1]+int(rect[0]/2)
	if (bottom >= h-offset):
		bottom = h-offset-1
	top = bottom-rect[0]
	if (top < 0):
		top = offset
	return top, bottom, left, right
	

#---------------------------------------------
# Find the brightest and darkest parts of
# a given image using a gaussian blur
#---------------------------------------------		
def find_min_max(img, gauss_radius):
	# From http://www.pyimagesearch.com/2014/09/29/finding-brightest-spot-image-using-python-opencv/
	# Gaussian blur radius must be odd
	if (gauss_radius % 2 == 0):
		gauss_radius = gauss_radius + 1
	img_blur = cv2.GaussianBlur(img, (gauss_radius, gauss_radius), 0)

	return img_blur, cv2.minMaxLoc(img_blur)
	
	
#---------------------------------------------
# Simple binary threshold
#---------------------------------------------		
def binary_threshold(img, lo, hi):
    # From http://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_imgproc/py_thresholding/py_thresholding.html
    ret, img_edges = cv2.threshold(img, lo, hi, cv2.THRESH_BINARY)
    return img_edges
	

#---------------------------------------------
# Simple adaptive threshold
#---------------------------------------------		
def adaptive_threshold(img, hi, window, c=2):
    # From http://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_imgproc/py_thresholding/py_thresholding.html
    img_edges = cv2.adaptiveThreshold(img, hi, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, window, c)
    return img_edges
	

#---------------------------------------------
# Threshold based on Otsu's method
#---------------------------------------------		
def otsu_threshold(img, lo, hi):
    # From http://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_imgproc/py_thresholding/py_thresholding.html
    ret, img_edges = cv2.threshold(img, lo, hi, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    return img_edges
	

#---------------------------------------------
# Get the all the centers and widths of a 
# simple step function
#---------------------------------------------		
def get_centers_and_widths(x, y, minThresh):
	from itertools import groupby
	from operator import itemgetter

	# Peaks need to be this tall to proceed
	peaks = np.where(y >= minThresh)[0]

	centers = []
	widths = []

	for k, g in groupby(enumerate(peaks), lambda ix : ix[0] - ix[1]):
		peak = list(map(itemgetter(1), g))

		left = x[peak[0]]
		width = len(peak)
		
		centers.append((width / 2.0) + left)
		widths.append(width)
		
	centers = np.array(centers)
	widths = np.array(widths)
		
	return centers, widths

#---------------------------------------------
# Get a list of strips
#---------------------------------------------		
def get_strips(x, y, minThresh, stdDev):

	centers, widths = get_centers_and_widths(x, y, minThresh)

	# Clean up outliers, which are probably dirt/scratches
	mean = np.mean(widths)
	std = np.std(widths)
	
	# Rough check that the mean is valid
	if (mean > 0):

		# Cull values that are stdDev standard deviations from the mean
		o = np.where(np.logical_and(widths <= mean + stdDev * std, widths >= mean - stdDev * std))[0]

		centers = centers[o]
		widths = widths[o]

	# If the mean is zero or negative, something bad happened
	else:
		centers = []
		widths = []

	return centers, widths
	
	
#---------------------------------------------
# Get the slopes of each point
#---------------------------------------------		
def get_angles(x, y, std):
	# Slope is rise over run
	dx = np.gradient(x)
	dy = np.gradient(y)
	
	a = np.tan(dy / dx)

	return a
	
	
#---------------------------------------------
# Given x and an angle, return the correct
# y value
#---------------------------------------------		
def correct_angles(x, y, a):
	import math

	dx = np.gradient(x)
	dy = math.atan(1) * dx
	
	y = y - dy
	#print(y)

	return y


#---------------------------------------------
# Process the region of interest
#---------------------------------------------		
def process_ROI(img, roi, step, offset, minThresh, stdDev):

	(start, stop, left, right) = roi
	img_p = img.copy()

	fits = []
	cols = []
	stripcount = []
	
	img_p = img[start:stop, left:right]

	# Iterate the image columns, incrementing by a step size
	for col in range(0, right-left-1, step):
		cols.append(col)

		y = np.zeros(stop-start)
		x = np.zeros(stop-start)
		
		# Extract a column from the image
		for row in range(0, stop-start-1):
			x[row] = row + start
			y[row] = y[row] + img_p[row][col]
				
		x = np.array(x)
		y = np.array(y)
		
		# Fit the peaks
		centers, widths = get_strips(x, y, minThresh, stdDev)
		
		# If any center registered as zero, cull it
		z = np.where(centers > 0)
		centers = centers[z]
		widths = widths[z]
		
		# Count the strips in this row
		stripcount.append(len(centers))

		# Amplitude is meaningless, set it to the threshold value
		amps = np.ones_like(centers) * minThresh
		# The mean is just the center
		means = centers
		# This is the RMS of the peak (integral of x^2 from 0 to width divided by width)
		# sqrt((1/3 width**3)/width) = sqrt(1/3) * width
		devs = np.sqrt(1.0/3.0) * widths
		
		# There's no real error on the amplitude in this method
		err_amps = np.ones_like(centers)
		# Assume the strip could have been wider by 2 pixels
		err_widths = 2.0 * np.ones_like(centers)
		# The error on the mean is (err_width)/width
		err_means = err_widths / widths
		# sqrt(1/3) * err_width
		err_devs = (np.sqrt(1.0/3.0) * err_widths) * np.ones_like(centers)

		# Check that the lists are all of equal length
		if (len(amps) and len(means) and len(devs)):
			# Sort the results by the mean
			a, m, s, ea, em, ed = zip(*sorted(zip(amps, means, devs, err_amps, err_means, err_devs), key=lambda pair: pair[1]))

			# Get the distances between means
			dd = tuple(np.gradient(m))

			fits.append([col, left, right, a, m, s, ea, em, ed, dd])
			
	return img_p, fits, min(stripcount)
	

	
#---------------------------------------------
# Convert a complicated data structure (a list
# of tuples) into a standard numpy array
#---------------------------------------------	
def to_array(data):

	length = len(sorted(data, key=len, reverse=True)[0])

	d = []
	for di in data:
		di_list = list(di)
		for i in range(len(di_list), length):
			di_list.append(None)

		d.append(di_list)
			
	d = np.array(d)
	return d
	

#---------------------------------------------
# Convert a list/array that was loaded as a
# string to a tuple of floats
#---------------------------------------------	
def parse_load_string(str):
	str = str.strip("[]") 
	str = str.strip("()") 
	vals = str.split(',')
	vals = tuple([float(v) for v in vals])
	return vals
	

#---------------------------------------------
# Load results from a CSV file
#---------------------------------------------	
def load_results(filename, header=True):

	import ast

	x = []
	means = []
	devs = []
	dx = []
	
	import csv
	with open(filename, mode='r') as infile:
		reader = csv.reader(infile, delimiter=',', quotechar='"')
		for rows in reader:
			if (len(rows) > 0):
				if (not header):
					x.append(parse_load_string(rows[0]))
					means.append(parse_load_string(rows[4]))
					devs.append(parse_load_string(rows[7]))
					dx.append(parse_load_string(rows[9]))
				else:
					header = False
	x = (np.array(x).T)[0]
	means = to_array(means)
	devs = to_array(devs)
	dx = to_array(dx)
	
	return x, means, devs, dx
	
#---------------------------------------------
# Save results to a CSV file
#---------------------------------------------		
def save_results(filename, results, header=None):
    import csv
    with open(filename, "w", newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        if (header):
            writer.writerow(header)
        for line in results:
            writer.writerow(line)
			

#---------------------------------------------
# Sometimes values are None, Inf, NaN, or
# negative.  These cause issues with plots and
# math operations like sqrt and log.
#---------------------------------------------
def fix_broken_values(vals, fixval):
    
    y = vals.copy()
    
    y[list(i for i, item in enumerate(y) if item is None)] = fixval
    y[list(i for i, item in enumerate(y) if np.isinf(item))] = fixval
    y[list(i for i, item in enumerate(y) if np.isnan(item))] = fixval
    y[y < 0] = fixval

    return y


#---------------------------------------------
# Calculate the chi-squared value for each
# observation
#---------------------------------------------	
def calc_chisquare_i(expected, observed, variance):
    return ((observed-expected)**2)/variance


#---------------------------------------------
# Calculate the sum of all the chi-squared 
# values and normalize by degrees of freedom
#---------------------------------------------	
def calc_chisquare(expected, observed, variance, dof):
    # Find source
    return np.sum(calc_chisquare_i(expected, observed, variance))/dof


#---------------------------------------------
# Get rid of outliers.  Any point in y
# exceeding a maximum y_max is culled, then
# any point with a chi-squared value greater
# than cs_max.
#
# WARNING!  Improper use of this function
# WILL affect your results!
#---------------------------------------------	
def detect_outliers(x, y, d, order, y_max, cs_max):

	# Anything more than y_max from the median gets a huge
	# error associated
	m = np.median(y)
	out = np.logical_or(y > m + y_max, y < m - y_max)

	s = d.copy()
	s[out] = 100000.0

	# numpy.polyfit() requires weights of the form 1/sigma, not
	# 1/sigma^2
	try:
		sqrt_s = np.sqrt(s)
	except:
		print(s.dtype)
		raise
		
	popt = np.polyfit(x, y, order, w=1.0/sqrt_s)
	
	# Generate expected values
	e = np.polyval(popt, x)

	# Get the chi-squared values for each point
	cs = calc_chisquare_i(e, y, d)

	try:
		# Keep only the points where the chi-squared is
		# less than the maximum
		vals = np.where(cs <= cs_max)[0]
	except:
		vals = []
		
	return vals
	

#---------------------------------------------
# Return the locations of n outliers.
# Useful for culling a few rogue points.
#
# WARNING!  Improper use of this function
# WILL affect your results!
#---------------------------------------------	
def detect_n_outliers(x, y, d, order, n):

	# numpy.polyfit() requires weights of the form 1/sigma, not
	# 1/sigma^2
	popt = np.polyfit(x, y, order, w=1.0/np.sqrt(d))

	# Generate expected values
	e = np.polyval(popt, x)

	# Get the chi-squared values for each point
	cs = calc_chisquare_i(e, y, d)

	# Generate an array of locations
	locs = np.array([i for i in range(len(y))])

	# Sort the chi-squared results
	cs, locs = zip(*sorted(zip(cs, locs), key=lambda pair: pair[0]))

	locs = locs[0:len(locs)-n-1]
	
	locs = sorted(locs)

	return locs
