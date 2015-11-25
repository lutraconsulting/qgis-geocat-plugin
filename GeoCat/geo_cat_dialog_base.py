# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'geo_cat_dialog_base.ui'
#
# Created: Wed Nov 25 10:29:25 2015
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_GeoCatDialogBase(object):
    def setupUi(self, GeoCatDialogBase):
        GeoCatDialogBase.setObjectName(_fromUtf8("GeoCatDialogBase"))
        GeoCatDialogBase.resize(601, 409)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/plugins/GeoCat/icon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        GeoCatDialogBase.setWindowIcon(icon)
        GeoCatDialogBase.setModal(True)
        self.gridLayout = QtGui.QGridLayout(GeoCatDialogBase)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.descriptionLabel = QtGui.QLabel(GeoCatDialogBase)
        self.descriptionLabel.setObjectName(_fromUtf8("descriptionLabel"))
        self.gridLayout.addWidget(self.descriptionLabel, 0, 0, 1, 1)
        self.searchPushButton = QtGui.QPushButton(GeoCatDialogBase)
        self.searchPushButton.setObjectName(_fromUtf8("searchPushButton"))
        self.gridLayout.addWidget(self.searchPushButton, 1, 2, 1, 1)
        self.resultsLabel = QtGui.QLabel(GeoCatDialogBase)
        self.resultsLabel.setObjectName(_fromUtf8("resultsLabel"))
        self.gridLayout.addWidget(self.resultsLabel, 2, 0, 1, 1)
        self.detailsLabel = QtGui.QLabel(GeoCatDialogBase)
        self.detailsLabel.setObjectName(_fromUtf8("detailsLabel"))
        self.gridLayout.addWidget(self.detailsLabel, 2, 1, 1, 1)
        self.resultsListWidget = QtGui.QListWidget(GeoCatDialogBase)
        self.resultsListWidget.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.resultsListWidget.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.resultsListWidget.setObjectName(_fromUtf8("resultsListWidget"))
        self.gridLayout.addWidget(self.resultsListWidget, 3, 0, 1, 1)
        self.detailsPlainTextEdit = QtGui.QPlainTextEdit(GeoCatDialogBase)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(2)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.detailsPlainTextEdit.sizePolicy().hasHeightForWidth())
        self.detailsPlainTextEdit.setSizePolicy(sizePolicy)
        self.detailsPlainTextEdit.setReadOnly(True)
        self.detailsPlainTextEdit.setObjectName(_fromUtf8("detailsPlainTextEdit"))
        self.gridLayout.addWidget(self.detailsPlainTextEdit, 3, 1, 1, 2)
        self.addSelectedPushButton = QtGui.QPushButton(GeoCatDialogBase)
        self.addSelectedPushButton.setEnabled(False)
        self.addSelectedPushButton.setObjectName(_fromUtf8("addSelectedPushButton"))
        self.gridLayout.addWidget(self.addSelectedPushButton, 4, 0, 1, 1)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.closePushButton = QtGui.QPushButton(GeoCatDialogBase)
        self.closePushButton.setObjectName(_fromUtf8("closePushButton"))
        self.horizontalLayout.addWidget(self.closePushButton)
        self.helpPushButton = QtGui.QPushButton(GeoCatDialogBase)
        self.helpPushButton.setObjectName(_fromUtf8("helpPushButton"))
        self.horizontalLayout.addWidget(self.helpPushButton)
        self.gridLayout.addLayout(self.horizontalLayout, 4, 2, 1, 1)
        self.searchLineEdit = QtGui.QLineEdit(GeoCatDialogBase)
        self.searchLineEdit.setObjectName(_fromUtf8("searchLineEdit"))
        self.gridLayout.addWidget(self.searchLineEdit, 1, 0, 1, 2)

        self.retranslateUi(GeoCatDialogBase)
        QtCore.QObject.connect(self.addSelectedPushButton, QtCore.SIGNAL(_fromUtf8("clicked()")), GeoCatDialogBase.add_selected_layers)
        QtCore.QObject.connect(self.searchPushButton, QtCore.SIGNAL(_fromUtf8("clicked()")), GeoCatDialogBase.search)
        QtCore.QObject.connect(self.resultsListWidget, QtCore.SIGNAL(_fromUtf8("currentRowChanged(int)")), GeoCatDialogBase.display_details)
        QtCore.QObject.connect(self.resultsListWidget, QtCore.SIGNAL(_fromUtf8("itemSelectionChanged()")), GeoCatDialogBase.on_result_sel_changed)
        QtCore.QObject.connect(self.searchLineEdit, QtCore.SIGNAL(_fromUtf8("returnPressed()")), GeoCatDialogBase.search)
        QtCore.QObject.connect(self.closePushButton, QtCore.SIGNAL(_fromUtf8("clicked()")), GeoCatDialogBase.reject)
        QtCore.QObject.connect(self.helpPushButton, QtCore.SIGNAL(_fromUtf8("clicked()")), GeoCatDialogBase.show_help)
        QtCore.QMetaObject.connectSlotsByName(GeoCatDialogBase)
        GeoCatDialogBase.setTabOrder(self.searchLineEdit, self.searchPushButton)
        GeoCatDialogBase.setTabOrder(self.searchPushButton, self.resultsListWidget)
        GeoCatDialogBase.setTabOrder(self.resultsListWidget, self.detailsPlainTextEdit)
        GeoCatDialogBase.setTabOrder(self.detailsPlainTextEdit, self.addSelectedPushButton)
        GeoCatDialogBase.setTabOrder(self.addSelectedPushButton, self.closePushButton)
        GeoCatDialogBase.setTabOrder(self.closePushButton, self.helpPushButton)

    def retranslateUi(self, GeoCatDialogBase):
        GeoCatDialogBase.setWindowTitle(_translate("GeoCatDialogBase", "Geo Cat", None))
        self.descriptionLabel.setText(_translate("GeoCatDialogBase", "Search for a layer based on general term (e.g. bats)", None))
        self.searchPushButton.setText(_translate("GeoCatDialogBase", "Search", None))
        self.resultsLabel.setText(_translate("GeoCatDialogBase", "Results", None))
        self.detailsLabel.setText(_translate("GeoCatDialogBase", "Details", None))
        self.addSelectedPushButton.setText(_translate("GeoCatDialogBase", "Add Selected", None))
        self.closePushButton.setText(_translate("GeoCatDialogBase", "Close", None))
        self.helpPushButton.setText(_translate("GeoCatDialogBase", "Help", None))

import resources_rc
