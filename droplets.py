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


def createRow(calib, interval, count, countDen):
    """
    Create row to output from interval of circles c to a CSV file

    returned list includes:
    minimum radius in mm
    maximum radius in mm
    mean radius in microns
    total droplet count
    average count per area
    number density N(r)
    """
    minR = interval[0] * calib
    maxR = interval[1] * calib
    return [minR, maxR, (minR + maxR) * 500, count, countDen, countDen / (maxR - minR)]


def merge(left, right):
    """Merge function used for merge sort"""
    lPoint = 0
    rPoint = 0
    result = []

    # Use two pointer method to build sorted list
    while lPoint < len(left) and rPoint < len(right):
        if left[lPoint][0] > right[rPoint][0]:  # Sort by min radius in descending order
            result.append(left[lPoint])
            lPoint += 1
        else:
            result.append(right[rPoint])
            rPoint += 1

    # Insert remaining terms from left or right
    if lPoint < len(left):
        for remaining in left[lPoint:]:
            result.append(remaining)
    elif rPoint < len(right):
        for remaining in right[rPoint:]:
            result.append(remaining)
    return result


def mergeSort(listOfLists):
    """Recursive merge sort used for sorting user entered settings in order of descending min radius"""
    if len(listOfLists) > 1:
        left = mergeSort(listOfLists[0:len(listOfLists) // 2])
        right = mergeSort(listOfLists[len(listOfLists) // 2:])
        return merge(left, right)
    else:
        return listOfLists


def main(settings, calib):
    calib = calib / 1000  # convert from microns to mm/pixel
    settings = mergeSort(settings)
    cCounts = np.array([0 for x in range(len(settings))])  # initialize circle count for each size range
    cCountsDen = np.array([0.0 for x in range(len(settings))])  # initialize circle count/area for each size range
    path = os.environ["PATH"]
    print('Image path: ' + path)
    outPath = os.environ["OUT"] + '/'
    print('Output path: ' + outPath)
    images, filenames = loadAllImages(path)

    # Output settings as csv
    print('Outputting settings to settings.csv')
    outRows = [["Calibration (microns/pix)", calib * 1000]]
    outRows.append(["Min Radius (pix)", "Max Radius (pix)", "Canny Edge Threshold", "Accumulator Threshold"])
    for row in settings:
        outRows.append(row)
    with open(outPath + 'settings.csv', 'w', newline='') as csvfile:
        filewriter = csv.writer(csvfile)
        filewriter.writerows(outRows)

    for imgNum, img in enumerate(images):
        print('Processing image: {}'.format(filenames[imgNum]))
        height, width = img.shape
        cimg = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        indices = []  # Indices for beginning of each section of circles
        cTotal = findCircles(img, cimg, settings[0][0] * 2, settings[0][2], settings[0][3], settings[0][0], settings[0][1])
        indices.append(len(cTotal))
        for i in range(1, len(settings)):
            cAdd = findCircles(img, cimg, settings[i][0] * 2, settings[i][2], settings[i][3], settings[i][0], settings[i][1])
            indices.append(sum(indices) + len(cAdd))
            cTotal = np.hstack((cTotal, cAdd))
        cTotal = cTotal[0]
        cLength = len(cTotal)

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
                    elif (np.linalg.norm(np.array([x1 - x2, y1 - y2])) + r2) < 1.1 * r1:
                        cTotal[j] = [0, 0, 0]
                        rowsToDelete.append(j)
                    else:
                        pass
        cTotal = np.delete(cTotal, rowsToDelete, axis=0)  # remaining circles
        cTotalR = np.delete(cTotal, [0, 1], axis=1)  # remaining radii only

        # Re-find indices of each section after inner circle deletion
        indices = np.array([np.argmax(cTotalR < settings[i][0]) for i in range(len(settings) - 1)])

        # Add counts/area of each size interval to total count (cCountsDen)
        if len(indices) == 0:
            cList = [cTotalR]
        else:
            cList = [cTotalR[indices[i]:indices[i + 1]] for i in range(len(indices) - 1)]
            cList.insert(0, cTotalR[0:indices[0]])  # Add first list of radii
            cList.append(cTotalR[indices[-1]:])  # Add last list of radii
        for i in range(len(cList)):
            cCounts[i] += len(cList[i])
            cCountsDen[i] += (len(cList[i]) / (calib**2 * height * width))

        # Draw circles onto a new image
        for i in cTotal:
            cv2.circle(cimg, (i[0], i[1]), i[2], (0, 255, 0), 2)
        cv2.imwrite('{}{}_out.jpg'.format(outPath, os.path.splitext(filenames[imgNum])[0]), cimg)

    # Output data as csv
    print('Outputting data to out.csv')
    outRows = [["Min r (mm)", "Max r (mm)", "Mean r (microns)", "Total Count (#)", "Count/Area (#/mm^3)", "N(r) (#/mm^3)"]]
    cCountsDen = cCountsDen / len(images)
    for i in range(len(cCountsDen)):
        outRows.append(createRow(calib, [settings[i][0], settings[i][1]], cCounts[i], cCountsDen[i]))
    with open(outPath + 'out.csv', 'w', newline='') as csvfile:
        filewriter = csv.writer(csvfile)
        filewriter.writerows(outRows)
