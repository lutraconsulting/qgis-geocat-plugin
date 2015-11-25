# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'config_dialog_base.ui'
#
# Created: Wed Nov 25 10:29:56 2015
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

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(412, 246)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/plugins/GeoCat/icon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        Dialog.setWindowIcon(icon)
        self.gridLayout = QtGui.QGridLayout(Dialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.postGisConnectionLabel = QtGui.QLabel(Dialog)
        self.postGisConnectionLabel.setObjectName(_fromUtf8("postGisConnectionLabel"))
        self.gridLayout.addWidget(self.postGisConnectionLabel, 0, 0, 1, 1)
        self.postGisConnectionComboBox = QtGui.QComboBox(Dialog)
        self.postGisConnectionComboBox.setMaximumSize(QtCore.QSize(1024, 16777215))
        self.postGisConnectionComboBox.setObjectName(_fromUtf8("postGisConnectionComboBox"))
        self.gridLayout.addWidget(self.postGisConnectionComboBox, 0, 1, 1, 1)
        self.MetadataTableSchemaLabel = QtGui.QLabel(Dialog)
        self.MetadataTableSchemaLabel.setObjectName(_fromUtf8("MetadataTableSchemaLabel"))
        self.gridLayout.addWidget(self.MetadataTableSchemaLabel, 1, 0, 1, 1)
        self.metadataTableSchemaComboBox = QtGui.QComboBox(Dialog)
        self.metadataTableSchemaComboBox.setObjectName(_fromUtf8("metadataTableSchemaComboBox"))
        self.gridLayout.addWidget(self.metadataTableSchemaComboBox, 1, 1, 1, 1)
        self.metadataTableNameLabel = QtGui.QLabel(Dialog)
        self.metadataTableNameLabel.setObjectName(_fromUtf8("metadataTableNameLabel"))
        self.gridLayout.addWidget(self.metadataTableNameLabel, 2, 0, 1, 1)
        self.metadataTableNameComboBox = QtGui.QComboBox(Dialog)
        self.metadataTableNameComboBox.setObjectName(_fromUtf8("metadataTableNameComboBox"))
        self.gridLayout.addWidget(self.metadataTableNameComboBox, 2, 1, 1, 1)
        self.titleColumnLabel = QtGui.QLabel(Dialog)
        self.titleColumnLabel.setObjectName(_fromUtf8("titleColumnLabel"))
        self.gridLayout.addWidget(self.titleColumnLabel, 3, 0, 1, 1)
        self.titleColumnComboBox = QtGui.QComboBox(Dialog)
        self.titleColumnComboBox.setObjectName(_fromUtf8("titleColumnComboBox"))
        self.gridLayout.addWidget(self.titleColumnComboBox, 3, 1, 1, 1)
        self.abstractColumnLabel = QtGui.QLabel(Dialog)
        self.abstractColumnLabel.setObjectName(_fromUtf8("abstractColumnLabel"))
        self.gridLayout.addWidget(self.abstractColumnLabel, 4, 0, 1, 1)
        self.abstractColumnComboBox = QtGui.QComboBox(Dialog)
        self.abstractColumnComboBox.setObjectName(_fromUtf8("abstractColumnComboBox"))
        self.gridLayout.addWidget(self.abstractColumnComboBox, 4, 1, 1, 1)
        self.layerSchemaNameLabel = QtGui.QLabel(Dialog)
        self.layerSchemaNameLabel.setObjectName(_fromUtf8("layerSchemaNameLabel"))
        self.gridLayout.addWidget(self.layerSchemaNameLabel, 5, 0, 1, 1)
        self.layerSchemaNameComboBox = QtGui.QComboBox(Dialog)
        self.layerSchemaNameComboBox.setObjectName(_fromUtf8("layerSchemaNameComboBox"))
        self.gridLayout.addWidget(self.layerSchemaNameComboBox, 5, 1, 1, 1)
        self.layerTableNameLabel = QtGui.QLabel(Dialog)
        self.layerTableNameLabel.setObjectName(_fromUtf8("layerTableNameLabel"))
        self.gridLayout.addWidget(self.layerTableNameLabel, 6, 0, 1, 1)
        self.layerTableNameComboBox = QtGui.QComboBox(Dialog)
        self.layerTableNameComboBox.setObjectName(_fromUtf8("layerTableNameComboBox"))
        self.gridLayout.addWidget(self.layerTableNameComboBox, 6, 1, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 8, 0, 1, 2)
        spacerItem = QtGui.QSpacerItem(20, 8, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 7, 1, 1, 1)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), Dialog.reject)
        QtCore.QObject.connect(self.postGisConnectionComboBox, QtCore.SIGNAL(_fromUtf8("currentIndexChanged(int)")), Dialog.on_connection_changed)
        QtCore.QObject.connect(self.metadataTableSchemaComboBox, QtCore.SIGNAL(_fromUtf8("currentIndexChanged(int)")), Dialog.on_metadata_schema_changed)
        QtCore.QObject.connect(self.metadataTableNameComboBox, QtCore.SIGNAL(_fromUtf8("currentIndexChanged(int)")), Dialog.on_metadata_table_changed)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), Dialog.all_done)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "Geo Cat Configuration", None))
        self.postGisConnectionLabel.setText(_translate("Dialog", "PostGIS Connection", None))
        self.MetadataTableSchemaLabel.setText(_translate("Dialog", "Metadata Table Schema", None))
        self.metadataTableNameLabel.setText(_translate("Dialog", "Metadata Table Name", None))
        self.titleColumnLabel.setText(_translate("Dialog", "Title Column", None))
        self.abstractColumnLabel.setText(_translate("Dialog", "Abstract Column", None))
        self.layerSchemaNameLabel.setText(_translate("Dialog", "Column for GIS Layer Schema Name", None))
        self.layerTableNameLabel.setText(_translate("Dialog", "Column for GIS Layer Table Name", None))

import resources_rc
