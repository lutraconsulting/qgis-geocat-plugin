# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeoCatDialog
                                 A QGIS plugin
 Search for PostGIS tables using metadata
                             -------------------
        begin                : 2015-11-24
        git sha              : $Format:%H$
        copyright            : (C) 2015 Dartmoor National Park Authority
        email                : gi@dartmoor.gov.uk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic
from PyQt4.QtCore import QUrl, QSettings
from dbutils import (
    get_postgres_connections,
    get_postgres_conn_info,
    get_connection,
    list_schemas,
    list_tables,
    list_columns
)

from qgis.core import (
    QgsDataSourceURI,
    QgsVectorLayer,
    QgsMapLayerRegistry
)

#FORM_CLASS, _ = uic.loadUiType(os.path.join(
#    os.path.dirname(__file__), 'config_dialog_base.ui'))
from config_dialog_base import Ui_Dialog


class GeoCatConfigDialog(QtGui.QDialog, Ui_Dialog):

    def __init__(self, parent=None):
        """Constructor."""
        super(GeoCatConfigDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.postGisConnectionComboBox.addItems(get_postgres_connections())

        # See if we can put back the old config
        s = QSettings()

        req_con = s.value('GeoCat/connection', '', type=str)
        req_met_tab_sc = s.value('GeoCat/metadataTableSchema', '', type=str)
        req_met_tab_ta = s.value('GeoCat/metadataTableName', '', type=str)
        req_title = s.value('GeoCat/titleColumn', '', type=str)
        req_abs = s.value('GeoCat/abstractColumn', '', type=str)
        req_lay_sch = s.value('GeoCat/gisLayerSchemaCol', '', type=str)
        req_lay_tab = s.value('GeoCat/gisLayerTableCol', '', type=str)

        self.postGisConnectionComboBox.blockSignals(True)
        self.metadataTableSchemaComboBox.blockSignals(True)
        self.metadataTableNameComboBox.blockSignals(True)
        self.titleColumnComboBox.blockSignals(True)
        self.abstractColumnComboBox.blockSignals(True)
        self.layerSchemaNameComboBox.blockSignals(True)
        self.layerTableNameComboBox.blockSignals(True)

        self.postGisConnectionComboBox.setCurrentIndex(
            self.postGisConnectionComboBox.findText(req_con)
        )

        if self.postGisConnectionComboBox.currentIndex() >= 0:

            self.refresh_schemas()

            self.metadataTableSchemaComboBox.setCurrentIndex(
                self.metadataTableSchemaComboBox.findText(req_met_tab_sc)
            )

            self.refresh_tables()

            self.metadataTableNameComboBox.setCurrentIndex(
                self.metadataTableNameComboBox.findText(req_met_tab_ta)
            )

            self.refresh_columns()

            self.titleColumnComboBox.setCurrentIndex(
                self.titleColumnComboBox.findText(req_title)
            )
            self.abstractColumnComboBox.setCurrentIndex(
                self.abstractColumnComboBox.findText(req_abs)
            )
            self.layerSchemaNameComboBox.setCurrentIndex(
                self.layerSchemaNameComboBox.findText(req_lay_sch)
            )
            self.layerTableNameComboBox.setCurrentIndex(
                self.layerTableNameComboBox.findText(req_lay_tab)
            )

        self.postGisConnectionComboBox.blockSignals(False)
        self.metadataTableSchemaComboBox.blockSignals(False)
        self.metadataTableNameComboBox.blockSignals(False)
        self.titleColumnComboBox.blockSignals(False)
        self.abstractColumnComboBox.blockSignals(False)
        self.layerSchemaNameComboBox.blockSignals(False)
        self.layerTableNameComboBox.blockSignals(False)

    def on_connection_changed(self):
        self.refresh_schemas()

    def on_metadata_schema_changed(self):
        self.refresh_tables()

    def on_metadata_table_changed(self):
        self.refresh_columns()

    def _get_cur(self):
        ci = get_postgres_conn_info(self.postGisConnectionComboBox.currentText())
        cur = get_connection(ci).cursor()
        return cur

    def refresh_schemas(self):
        cur = self._get_cur()
        schemas = list_schemas(cur)
        self.metadataTableSchemaComboBox.clear()
        self.metadataTableSchemaComboBox.addItems(schemas)

    def refresh_tables(self):
        cur = self._get_cur()
        tables = list_tables(cur, self.metadataTableSchemaComboBox.currentText())
        self.metadataTableNameComboBox.clear()
        self.metadataTableNameComboBox.addItems(tables)

    def refresh_columns(self):
        cur = self._get_cur()
        cols = list_columns(cur,
                            self.metadataTableSchemaComboBox.currentText(),
                            self.metadataTableNameComboBox.currentText())

        self.titleColumnComboBox.clear()
        self.titleColumnComboBox.addItems(cols)

        self.abstractColumnComboBox.clear()
        self.abstractColumnComboBox.addItems(cols)

        self.layerSchemaNameComboBox.clear()
        self.layerSchemaNameComboBox.addItems(cols)

        self.layerTableNameComboBox.clear()
        self.layerTableNameComboBox.addItems(cols)

    def all_done(self):
        s = QSettings()
        s.setValue("GeoCat/connection", self.postGisConnectionComboBox.currentText())
        s.setValue("GeoCat/metadataTableSchema", self.metadataTableSchemaComboBox.currentText())
        s.setValue("GeoCat/metadataTableName", self.metadataTableNameComboBox.currentText())
        s.setValue("GeoCat/titleColumn", self.titleColumnComboBox.currentText())
        s.setValue("GeoCat/abstractColumn", self.abstractColumnComboBox.currentText())
        s.setValue("GeoCat/gisLayerSchemaCol", self.layerSchemaNameComboBox.currentText())
        s.setValue("GeoCat/gisLayerTableCol", self.layerTableNameComboBox.currentText())
        self.accept()
