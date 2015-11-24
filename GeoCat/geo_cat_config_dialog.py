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
from PyQt4.QtCore import QUrl
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

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'config_dialog_base.ui'))


class GeoCatConfigDialog(QtGui.QDialog, FORM_CLASS):

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
        pass