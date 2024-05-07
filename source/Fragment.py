# PIUI
# Papyrus Intelligent User Interface for Assembling Fragments and Analysis
#
# Copyright(C) 2022
# Visual Computing Lab
# ISTI - Italian National Research Council
# All rights reserved.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License (http://www.gnu.org/licenses/gpl.txt)
# for more details.

import numpy as np

from skimage import measure
from PyQt5.QtGui import QImage, QPixmap, QPainterPath, QPolygonF
from PyQt5.QtCore import QPointF

from source.utils import qimageToNumpyArray

"""
compute the bounding box of a set of points in format [[x0, y0], [x1, y1]... ]
padding is used, since when painting we draw a 'fat' line
"""
def pointsBox(points, pad = 0):
    box = [points[:, 1].min()-pad,
           points[:, 0].min()-pad,
           points[:, 0].max() + pad,
           points[:, 1].max() + pad]
    box[2] -= box[1]
    box[3] -= box[0]
    return np.array(box).astype(int)

class Fragment(object):
    """
    Fragment represents a fragment belonging to the papyrus.
    It can be tagged such that it belongs to a specific group and annotated.
    It is stored as an RGB image (typically of small size).
    The BACK of the fragment is also stored, if available.
    """

    def __init__(self, filename, offset_x, offset_y, id):

        self.id = int(id)
        self.filename = filename
        self.bbox = [offset_y, offset_x, 0, 0]
        self.group_id = -1
        self.note = ""
        self.center = np.array((offset_x, offset_y))

        # custom user data - not used for now
        self.data = {}

        self.contour = None
        self.inner_contours = []

        self.qimage = None
        self.qimage_back = None
        self.qpixmap = None
        self.qpixmap_back = None
        self.qpixmap_item = None
        self.qpixmap_back_item = None
        self.qpath = None
        self.qpath_item = None
        self.qpath_back_item = None
        self.id_item = None
        self.id_back_item = None

        # load image
        if filename != "":

            self.qimage = QImage(filename)

            filename_back = filename[:-4] + "_back" + filename[-4:]
            self.qimage_back = QImage(filename_back)

            # BBOX FORMAT: top, left, width, height
            self.bbox = [offset_y, offset_x, self.qimage.width(), self.qimage.height()]

            # center is (x, y)
            self.center = np.array((offset_x + self.qimage.width()/2, offset_y + self.qimage.height()/2))

            self.prepareForDrawing()

    def setId(self, id):

        self.id = id

    def createMask(self, qimage):

        mask = np.zeros((self.bbox[3], self.bbox[2]), dtype=np.uint8)
        img = qimageToNumpyArray(qimage)

        # turn on opaque pixels
        mask[img[:, :, 3] > 0] = 255

        return mask

    def createContourFromMask(self, mask):
        """
        It creates the contour (and the corrisponding polygon) from the blob mask.
        """

        if self.inner_contours is not None: 
            self.inner_contours.clear()
        if self.contour is not None:
            self.contour.clear()
        return 

        # we need to pad the mask to avoid to break the contour that touches the borders
        PADDED_SIZE = 4

        img_padded = np.pad(mask, (PADDED_SIZE, PADDED_SIZE), mode="constant", constant_values=(0, 0))

        contours = measure.find_contours(img_padded, 0.6)
        inner_contours = measure.find_contours(img_padded, 0.4)
        number_of_contours = len(contours)

        threshold = 20  # min number of points in a small hole

        if number_of_contours > 1:

            # search the contour with the largest bounding box (area)
            max_area = 0
            longest = 0
            for i, contour in enumerate(contours):
                cbox = pointsBox(contour, 0)
                area = cbox[2] * cbox[3]
                if area > max_area:
                    max_area = area
                    longest = i

            max_area = 0
            inner_longest = 0
            for i, contour in enumerate(inner_contours):
                cbox = pointsBox(contour, 0)
                area = cbox[2] * cbox[3]
                if area > max_area:
                    max_area = area
                    inner_longest = i

            # divide the contours in OUTER contour and INNER contours
            for i, contour in enumerate(contours):
                if i == longest:
                    self.contour = np.array(contour)

            for i, contour in enumerate(inner_contours):
                if i != inner_longest:
                    if contour.shape[0] > threshold:
                        coordinates = np.array(contour)
                        self.inner_contours.append(coordinates)

            # adjust the coordinates of the outer contour
            # (NOTE THAT THE COORDINATES OF THE BBOX ARE IN THE GLOBAL MAP COORDINATES SYSTEM)
            for i in range(self.contour.shape[0]):
                ycoor = self.contour[i, 0]
                xcoor = self.contour[i, 1]
                self.contour[i, 0] = xcoor - PADDED_SIZE + self.bbox[1]
                self.contour[i, 1] = ycoor - PADDED_SIZE + self.bbox[0]

            # adjust coordinates of the INNER contours
            for j, contour in enumerate(self.inner_contours):
                for i in range(contour.shape[0]):
                    ycoor = contour[i, 0]
                    xcoor = contour[i, 1]
                    self.inner_contours[j][i, 0] = xcoor - PADDED_SIZE + self.bbox[1]
                    self.inner_contours[j][i, 1] = ycoor - PADDED_SIZE + self.bbox[0]
        elif number_of_contours == 1:

            coords = measure.approximate_polygon(contours[0], tolerance=0.2)
            self.contour = np.array(coords)

            # adjust the coordinates of the outer contour
            # (NOTE THAT THE COORDINATES OF THE BBOX ARE IN THE GLOBAL MAP COORDINATES SYSTEM)
            for i in range(self.contour.shape[0]):
                ycoor = self.contour[i, 0]
                xcoor = self.contour[i, 1]
                self.contour[i, 0] = xcoor - PADDED_SIZE + self.bbox[1]
                self.contour[i, 1] = ycoor - PADDED_SIZE + self.bbox[0]
        else:
            raise Exception("Empty contour")

    def getImage(self):

        if self.qimage is not None:
            nparray = qimageToNumpyArray(self.qimage)
        else:
            nparray = None
        return nparray

    def getImageBack(self):

        if self.qimage_back is not None:
            nparray = qimageToNumpyArray(self.qimage_back)
        else:
            nparray = None
        return nparray

    def updatePosition(self, dx, dy):

        self.center[0] += dx
        self.center[1] += dy

        self.bbox[0] += dy
        self.bbox[1] += dx

        if self.contour is not None:
            self.contour[:, 0] += dx
            self.contour[:, 1] += dy

        for inner_contour in self.inner_contours:
            inner_contour[:, 0] += dx
            inner_contour[:, 1] += dy
    
    def setPosition(self, newX, newY):

        self.center[0] = newX
        self.center[1] = newY

        self.bbox[0] = newY
        self.bbox[1] = newX

        if self.contour is not None:
            self.contour[:, 0] = newX
            self.contour[:, 1] = newY

        for inner_contour in self.inner_contours:
            inner_contour[:, 0] = newX
            inner_contour[:, 1] = newY

    def prepareForDrawing(self, back=False):
        """
        Create the QPixmap and the QPainterPath to highlight the contour of the selected fragments.
        """

        if back is True:
            self.qpixmap_back = QPixmap.fromImage(self.qimage_back)
        else:
            self.qpixmap = QPixmap.fromImage(self.qimage)

        mask = self.createMask(self.qimage)
        m = measure.moments(mask)
        c = np.array((m[0, 1] / m[0, 0], m[1, 0] / m[0, 0]))
        self.center = np.array((c[0] + self.bbox[1], c[1] + self.bbox[0]))

        self.createContourFromMask(mask)

        return 

        # QPolygon to draw the blob
        qpolygon = QPolygonF()
        for i in range(self.contour.shape[0]):
            qpolygon << QPointF(self.contour[i, 0] + 0.5, self.contour[i, 1] + 0.5)

        self.qpath = QPainterPath()
        self.qpath.addPolygon(qpolygon)

        for inner_contour in self.inner_contours:
            qpoly_inner = QPolygonF()
            for i in range(inner_contour.shape[0]):
                qpoly_inner << QPointF(inner_contour[i, 0] + 0.5, inner_contour[i, 1] + 0.5)

            path_inner = QPainterPath()
            path_inner.addPolygon(qpoly_inner)
            self.qpath = self.qpath.subtracted(path_inner)

    def fromDict(self, dict):
        """
        Set the blob information given it represented as a dictionary.
        """

        self.filename = dict["filename"]
        self.id = int(dict["id"])
        self.group_id = int(dict["group id"])
        self.note = dict["note"]
        self.bbox = dict["bbox"]
        self.center = np.asarray(dict["center"])
        self.filename = dict["filename"]
        self.contour = np.asarray(dict["contour"])
        self.inner_contours = []
        for c in dict["inner contours"]:
            self.inner_contours.append(np.asarray(c))

        if self.filename != "":
            self.qimage = QImage(self.filename)
            filename_back = self.filename[:-4] + "_back" + self.filename[-4:]
            self.qimage_back = QImage(filename_back)

            self.prepareForDrawing()


    def createContour(self):
        pass

    def save(self):
        return self.toDict()

    def toDict(self):
        """
        Put the fragment information in a dictionary.
        """

        dict = {}

        dict["filename"] = self.filename
        dict["id"] = self.id
        dict["group id"] = self.group_id
        dict["note"] = self.note
        dict["bbox"] = self.bbox
        dict["center"] = self.center.tolist()
        dict["contour"] = self.contour.tolist()
        dict["inner contours"] = []
        for c in self.inner_contours:
            dict["inner contours"].append(c.tolist())

        return dict


