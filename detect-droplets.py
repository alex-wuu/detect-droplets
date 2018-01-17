import numpy as np
import cv2
import csv
import os


def loadAllImages(path):
	"""Load all images in the specified path"""
	images = []
	filenames = []
	for filename in os.listdir(path):
		img = cv2.imread(os.path.join(path, filename), 0)
		if img is not None:
			images.append(img)
			filenames.append(filename)
	return images, filenames


def findCircles(img, cimg, minDist, p1, p2, minR, maxR):
	"""Use hough circles to find circles in img"""
	circles = cv2.HoughCircles(img, cv2.HOUGH_GRADIENT, 1, minDist, param1=p1, param2=p2, minRadius=minR, maxRadius=maxR)
	if circles is not None:
		circles = np.int32(np.around(circles))
	else:
		circles = [[[0, 0, 0]]]
	return circles


def createRow(calib, interval, count):
	"""
	Create row to output from interval of circles c to a CSV file

	returned list includes:
	minimum radius in mm
	maximum radius in mm
	mean radius in microns
	average count per area
	number density N(r)
	"""
	minR = interval[0] * calib
	maxR = interval[1] * calib
	return [minR, maxR, (minR + maxR) * 500, count, count / (maxR - minR)]


if __name__ == "__main__":
	calib = 4.2623 / 1000  # mm/pixel
	minRs = [100, 50, 30, 15, 10]  # minimum radii for hough circles
	maxRs = [200, *minRs[:-1]]  # maximum radii for hough circles
	cCounts = np.array([0.0 for x in range(len(minRs))])  # initialize circle count/area for each size range
	path = 'PATH_TO_YOUR_IMAGES_HERE'
	images, filenames = loadAllImages(path)
	for imgNum, img in enumerate(images):
		print('Processing image: {}'.format(filenames[imgNum]))
		height, width = img.shape
		cimg = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
		c0 = findCircles(img, cimg, 200, 150, 70, minRs[0], maxRs[0])
		c1 = findCircles(img, cimg, 100, 75, 55, minRs[1], maxRs[1])
		c2 = findCircles(img, cimg, 60, 40, 55, minRs[2], maxRs[2])
		c3 = findCircles(img, cimg, 30, 250, 30, minRs[3], maxRs[3])
		c4 = findCircles(img, cimg, 20, 40, 22, minRs[4], maxRs[4])
		cTotal = np.hstack((c0, c1, c2, c3, c4))[0]
		cLength = len(cTotal)

		# Indices for beginning of each section of circles
		indices = np.cumsum(np.array([len(c0[0]), len(c1[0]), len(c2[0]), len(c3[0]), len(c4[0])]))

		# Delete inner circles
		rowsToDelete = []
		for i in range(cLength):
			x1, y1, r1 = cTotal[i]
			if (x1, y1, r1) == (0, 0, 0):
				pass
			else:
				# section is used to make sure only smaller circles are checked
				section = 0
				for index in indices:
					if i < index:
						section = index
						break
				if section == cLength:
					break  # no more droplets can be deleted, break early
				for j in range(section, cLength):
					x2, y2, r2 = cTotal[j]
					if (x2, y2, r2) == (0, 0, 0) or i == j or r1 < r2:
						pass
					elif (np.linalg.norm(np.array([x1-x2, y1-y2])) + r2) < 1.1 * r1:
						cTotal[j] = [0, 0, 0]
						rowsToDelete.append(j)
					else:
						pass
		cTotal = np.delete(cTotal, rowsToDelete, axis=0)  # remaining circles
		cTotalR = np.delete(cTotal, [0, 1], axis=1)  # remaining radii only

		# Re-find indices of each section after inner circle deletion
		indices = np.array([np.argmax(cTotalR < 100), np.argmax(cTotalR < 50), np.argmax(cTotalR < 30), np.argmax(cTotalR < 15)])

		# Add counts/area of each size interval to total count (cCounts)
		cList = [cTotalR[0:indices[0]], cTotalR[indices[0]:indices[1]], cTotalR[indices[1]:indices[2]], cTotalR[indices[2]:indices[3]], cTotalR[indices[3]:]]
		for i in range(len(cList)):
			cCounts[i] += (len(cList[i]) / (calib**2 * height * width))

		# Draw circles onto a new image
		for i in cTotal:
			cv2.circle(cimg, (i[0], i[1]), i[2], (0, 255, 0), 2)
		cv2.imwrite('{}{}_out.jpg'.format(path, os.path.splitext(filenames[imgNum])[0]), cimg)

	# Output data as csv
	print('Outputting data to out.csv')
	outRows = [["Min r (mm)", "Max r (mm)", "Mean r (microns)", "Count/Area (#/mm^3)", "N(r) (#/mm^3)"]]
	cCounts = cCounts / len(images)
	for i in range(len(cCounts)):
		outRows.append(createRow(calib, [minRs[i], maxRs[i]], cCounts[i]))
	with open(path + 'out.csv', 'w', newline='') as csvfile:
		filewriter = csv.writer(csvfile)
		filewriter.writerows(outRows)
