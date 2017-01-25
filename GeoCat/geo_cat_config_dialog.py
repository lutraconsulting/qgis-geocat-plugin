# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Layer Metadata Search
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

# noinspection PyPackageRequirements
from PyQt4.QtGui import (
    QDialog,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QRadioButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QDateEdit
)
from PyQt4.QtCore import QSettings
from dbutils import (
    get_postgres_connections,
    get_postgres_conn_info,
    get_connection,
    list_schemas,
    list_tables,
    list_columns
)
from .gc_utils import load_ui


FORM_CLASS = load_ui('config_dialog_base')


class GeoCatConfigDialog(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)

        # signals
        self.postGisConnectionComboBox.currentIndexChanged.connect(self.on_connection_changed)
        self.metadataTableSchemaComboBox.currentIndexChanged.connect(self.on_metadata_schema_changed)
        self.metadataTableNameComboBox.currentIndexChanged.connect(self.on_metadata_table_changed)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.accepted.connect(self.all_done)

        # TODO: if a defined connection is broken in any way,
        # this will raise an exception here
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

        self.block_widgets_signals(class_list=[QComboBox])

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

            self.block_widgets_signals(block=False, class_list=[QComboBox])

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


    def block_widgets_signals(self, block=True, class_list=[]):
        for cl in class_list:
            for w in self.findChildren(cl):
                w.blockSignals(block)