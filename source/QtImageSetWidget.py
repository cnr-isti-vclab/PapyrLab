#
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
#GNU General Public License (http://www.gnu.org/licenses/gpl.txt)
# for more details.

import os

from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QLabel, QComboBox, QMessageBox, QScrollArea, QSizePolicy, \
    QHBoxLayout, QVBoxLayout, QGridLayout

from source.Fragment import Fragment

class QMiniImage(QWidget):

    THUMB_SIZE = 200

    def __init__(self, fragment, parent=None):
        super(QMiniImage, self).__init__(parent)

        layout_V = QVBoxLayout()
        pxmap = fragment.qpixmap.copy()
        pxmap = pxmap.scaled(self.THUMB_SIZE, self.THUMB_SIZE, Qt.KeepAspectRatio)
        self.lbl = QLabel()
        self.lbl.setPixmap(pxmap)
        layout_V.addWidget(self.lbl)
        label = os.path.basename(fragment.filename)
        layout_V.addWidget(QLabel(label))

        layout_V.setAlignment(Qt.AlignCenter)
        self.setLayout(layout_V)

        self.ref = fragment

class QtImageSetWidget(QWidget):

    select = pyqtSignal()

    def __init__(self, project, parent=None):
        super(QtImageSetWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(70,70,70); color: white")
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        self.NCOLS = 1

        self.combo_group = QComboBox()
        self.combo_group.addItem("All")
        lbl = QLabel("Group: ")
        lbl.setFixedWidth(90)
        hlayout = QHBoxLayout()
        hlayout.addWidget(lbl)
        hlayout.addWidget(self.combo_group)

        self.combo_group.currentIndexChanged.connect(self.groupChanged)

        self.scroll_area = QScrollArea()
        self.scroll_area.setMinimumWidth(200)
        self.scroll_area.setMinimumHeight(200)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.grid_widget = None
        self.grid_layout = None
        self.setupImages(project.fragments)

        main_layout = QVBoxLayout()
        main_layout.addLayout(hlayout)
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)

        self.parent = parent

    pyqtSlot(int)
    def groupChanged(self, index):
        if index < 0:   # FIXME: this should not happen
            return
        
        txt = self.combo_group.itemText(index)

        if txt == "All":
            for mini_image in self.mini_images:
                mini_image.setVisible(True)
        else:
            try:
                group_id = int(txt)
            except:
                return

            for mini_image in self.mini_images:
                fragment = mini_image.ref
                if fragment.group_id == group_id:
                    mini_image.setVisible(True)
                else:
                    mini_image.setVisible(False)

        self.updateScrollArea()

    def setProject(self, project):

        self.setupImages(project.fragments)

    def setupImages(self, fragments):

        self.mini_images = []
        self.mini_images_back = [] # TODO: add verso mini images

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout()

        self.grid_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.grid_widget.setMinimumWidth(400)
        self.grid_widget.setMinimumHeight(220)
        self.grid_widget.setLayout(self.grid_layout)

        for fragment in fragments:
            if isinstance(fragment, Fragment):
                self.addImage(fragment)

        self.scroll_area.setWidget(self.grid_widget)

    def addImage(self, fragment):

        exists = False
        for mini_image in self.mini_images:
            if mini_image.ref == fragment:
                exists = True
                break

        if not exists:
            mini_image = QMiniImage(fragment)
            self.mini_images.append(mini_image)
            n = len(self.mini_images)
            row = n / self.NCOLS
            col = n % self.NCOLS
            self.grid_layout.addWidget(mini_image, int(row), int(col))

            # Connect the click event to highlight the selected item
            mini_image.mousePressEvent = lambda event, img=mini_image: self.highlightItem(img, reset_fragment_selection=True)

    def clearHighlights(self):
        for mini_image in self.mini_images:
            mini_image.lbl.setStyleSheet("")

    def highlightItem(self, item, center=True, reset_fragment_selection=False):
        self.clearHighlights()
        item.lbl.setStyleSheet("background-color: lightgray;")
        if reset_fragment_selection:
            self.parent.viewerplus.resetSelection()
        self.parent.viewerplus.addToSelectedList(item.ref)
        if center:
            self.parent.viewerplus.centerOn(item.ref.center[0], item.ref.center[1])

    def updateComboGroups(self):

        self.combo_group.clear()
        self.combo_group.addItem("All")

        group_ids = set()
        for mini_image in self.mini_images:
            fragment = mini_image.ref
            if fragment.group_id >= 0:
                group_ids.add(fragment.group_id)

        group_ids = list(group_ids)
        group_ids.sort()
        for group_id in group_ids:
            self.combo_group.addItem(str(group_id))

    def scrollToFragment(self, fragment, verso=False):
        mini_images = self.mini_images_back if verso else self.mini_images
        for mini_image in mini_images:
            if mini_image.ref == fragment:
                self.scroll_area.ensureWidgetVisible(mini_image)
                self.highlightItem(mini_image, center=False)

    def removeImages(self, fragments):

        for fragment in fragments:
            mini_image_list = self.mini_images.copy()
            for mini_image in self.mini_images:
                if mini_image.ref == fragment:
                    mini_image_list.remove(mini_image)
                    self.grid_layout.removeWidget(mini_image)

            self.mini_images = mini_image_list

            self.updateScrollArea()

    def updateScrollArea(self):

        # update scroll area through reparenting

        self.grid_widget = QWidget()
        self.grid_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.grid_widget.setMinimumWidth(400)
        self.grid_widget.setMinimumHeight(220)
        self.grid_widget.setLayout(self.grid_layout)
        self.scroll_area.setWidget(self.grid_widget)

    def mousePressEvent(self, event):
        """
        Left button select an image
        """

        mods = event.modifiers()

        if event.button() == Qt.LeftButton:
            pass


