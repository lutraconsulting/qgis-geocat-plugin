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

# noinspection PyPackageRequirements
from PyQt4.QtGui import (
    QDialog,
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
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
from errors import CustomColumnException
from user_communication import UserCommunication


FORM_CLASS = load_ui('config_dialog_base')


class GeoCatConfigDialog(QDialog, FORM_CLASS):

    def __init__(self, iface, parent=None):
        # import pydevd; pydevd.settrace(suspend=False)
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.iface = iface
        self.uc = UserCommunication(iface, 'Metadata Plugin')
        self.cust_cols = []

        # signals
        self.postGisConnectionComboBox.currentIndexChanged.connect(self.on_connection_changed)
        self.metadataTableSchemaComboBox.currentIndexChanged.connect(self.on_metadata_schema_changed)
        self.metadataTableNameComboBox.currentIndexChanged.connect(self.on_metadata_table_changed)
        self.addCustomColumnBtn.clicked.connect(self.add_custom_column)
        self.removeCustomColumnBtn.clicked.connect(self.remove_custom_column)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.accepted.connect(self.all_done)

        # See if we can put back the old config
        s = QSettings()
        s.beginGroup('GeoCat')
        dlg_width = s.value('settingsDialogWidth', 0, type=int)
        req_con = s.value('connection', '', type=str)
        req_met_tab_sc = s.value('metadataTableSchema', '', type=str)
        req_met_tab_ta = s.value('metadataTableName', '', type=str)
        req_title = s.value('titleColumn', '', type=str)
        req_abs = s.value('abstractColumn', '', type=str)
        req_lay_sch = s.value('gisLayerSchemaCol', '', type=str)
        req_lay_tab = s.value('gisLayerTableCol', '', type=str)
        req_lay_type = s.value('gisLayerTypeCol', '', type=str)
        req_ras_path = s.value('gisRasterPathCol', '', type=str)
        ignore_col = s.value('ignoreCol', '', type=str)
        private_col = s.value('privateCol', '', type=str)
        qgis_connection = s.value('qgisConnectionCol', '', type=str)
        vector_identifier = s.value('vectorIdentifier', 'vector', type=str)
        raster_identifier = s.value('rasterIdentifier', 'raster', type=str)
        wms_identifier = s.value('wmsIdentifier', 'wms', type=str)
        view_primary_key = s.value('viewPrimaryKey', 'id', type=str)

        if dlg_width != 0:
            self.resize(dlg_width, self.height())
        self.block_widgets_signals(class_list=[QComboBox])

        self.vectorIdentifierLineEdit.setText(vector_identifier)
        self.rasterIdentifierLineEdit.setText(raster_identifier)
        self.wmsIdentifierLineEdit.setText(wms_identifier)
        self.view_pk_le.setText(view_primary_key)

        # TODO: if a defined connection is broken in any way,
        # this will raise an exception here
        self.postGisConnectionComboBox.addItems(get_postgres_connections())

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
            self.layerTypeComboBox.setCurrentIndex(
                self.layerTypeComboBox.findText(req_lay_type)
            )
            self.rasterPathComboBox.setCurrentIndex(
                self.rasterPathComboBox.findText(req_ras_path)
            )

            self.get_custom_columns()

            self.ignoreComboBox.setCurrentIndex(
                self.ignoreComboBox.findText(ignore_col)
            )

            self.privateComboBox.setCurrentIndex(
                self.privateComboBox.findText(private_col)
            )

            self.qgis_connection_cbo.setCurrentIndex(
                self.qgis_connection_cbo.findText(qgis_connection)
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

    def add_custom_column(self):
        self.set_custom_columns_settings()
        s = QSettings()
        s.beginGroup('GeoCat/CustomColumns')
        cc_nr = str(len(s.childGroups()))
        s.beginGroup(cc_nr)
        s.setValue('desc', '')
        s.setValue('col', '')
        s.setValue('widget', 'QLineEdit')
        self.get_custom_columns()

    def remove_custom_column(self):
        s = QSettings()
        s.beginGroup('GeoCat/CustomColumns')
        last_col = s.childGroups()[-1]
        s.remove(last_col)
        self.get_custom_columns()

    def get_custom_columns(self):
        self.clear_layout(self.customColsLayout)
        self.removeCustomColumnBtn.setDisabled(True)
        cur = self._get_cur()
        cols = list_columns(cur,
                            self.metadataTableSchemaComboBox.currentText(),
                            self.metadataTableNameComboBox.currentText())
        classes = [
            ['QLineEdit (single line)', 'QLineEdit'],
            ['QTextEdit (multiple lines)', 'QTextEdit'],
            ['QDateEdit', 'QDateEdit']
        ]
        s = QSettings()
        s.beginGroup('GeoCat/CustomColumns')
        self.cust_cols = []
        for i, cc in enumerate(sorted(s.childGroups(), key=int)):
            self.removeCustomColumnBtn.setEnabled(True)
            self.cust_cols.insert(i, {})
            s.beginGroup(cc)
            desc = s.value('desc')
            col = s.value('col')
            wclass = s.value('widget', 'QLineEdit')
            self.cust_cols[i]['desc'] = desc
            self.cust_cols[i]['col'] = col
            self.cust_cols[i]['widget'] = wclass

            # create custom column widget
            # Where user specify description, column and widget class
            w = QWidget()
            w.setObjectName('cc_widget_{}'.format(i))
            lout = QHBoxLayout()

            # description widget
            desc_w = QLineEdit()
            desc_w.setObjectName('cc_desc_ledit_{}'.format(i))
            desc_w.setText(desc)
            lout.addWidget(desc_w)

            # column widget
            col_w = QComboBox()
            col_w.addItems(cols)
            col_w.setObjectName('cc_col_cbo_{}'.format(i))
            col_w.setCurrentIndex(col_w.findText(col))
            lout.addWidget(col_w)

            # widget class widget
            cla_w = QComboBox()
            for c in classes:
                cla_w.addItem(c[0], c[1])
            cla_w.setObjectName('cc_class_cbo_{}'.format(i))
            cla_w.setCurrentIndex(cla_w.findData(wclass))
            lout.addWidget(cla_w)

            lout.setMargin(0)
            w.setLayout(lout)
            self.customColsLayout.addWidget(w)
            s.endGroup()

    def set_custom_columns_settings(self):
        classes = ['QLineEdit', 'QTextEdit', 'QDateEdit']
        s = QSettings()
        s.beginGroup('GeoCat/CustomColumns')
        s.remove('')
        for i, cc in enumerate(self.cust_cols):
            s.beginGroup(str(i))
            s.remove('')

            desc_w = self.findChild(QLineEdit, 'cc_desc_ledit_{}'.format(i))
            desc = desc_w.text()
            s.setValue('desc', desc)

            col_name = self.findChild(QComboBox, 'cc_col_cbo_{}'.format(i)).currentText()
            s.setValue('col', col_name)

            cla_name_cbo = self.findChild(QComboBox, 'cc_class_cbo_{}'.format(i))
            cla_name = classes[cla_name_cbo.currentIndex()]
            s.setValue('widget', cla_name)

            s.endGroup()

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

        self.layerTypeComboBox.clear()
        self.layerTypeComboBox.addItems(cols)

        self.rasterPathComboBox.clear()
        self.rasterPathComboBox.addItems(cols)

        self.ignoreComboBox.clear()
        self.ignoreComboBox.addItem('--DISABLED--')
        self.ignoreComboBox.addItems(cols)

        self.privateComboBox.clear()
        self.privateComboBox.addItem('--DISABLED--')
        self.privateComboBox.addItems(cols)

        self.qgis_connection_cbo.clear()
        self.qgis_connection_cbo.addItem('--DISABLED--')
        self.qgis_connection_cbo.addItems(cols)

    def check_custom_cols(self):
        cur = self._get_cur()
        cols = list_columns(cur,
                            self.metadataTableSchemaComboBox.currentText(),
                            self.metadataTableNameComboBox.currentText())
        for i, cc in enumerate(self.cust_cols):
            desc_w = self.findChild(QLineEdit, 'cc_desc_ledit_{}'.format(i))
            desc = desc_w.text()
            if not desc:
                msg = 'Empty description of custom column. Enter a description or remove the custom column.'
                self.uc.log_info(msg)
                self.uc.show_warn(msg)
                raise CustomColumnException

            col_name = self.findChild(QComboBox, 'cc_col_cbo_{}'.format(i)).currentText()
            if col_name not in cols:
                msg = 'Metadata table column not set. Make a choice or remove the custom column.'
                self.uc.log_info(msg)
                self.uc.show_warn(msg)
                raise CustomColumnException

    def all_done(self):
        try:
            self.check_custom_cols()
        except CustomColumnException:
            return
        s = QSettings()
        s.setValue("GeoCat/connection", self.postGisConnectionComboBox.currentText())
        s.setValue("GeoCat/metadataTableSchema", self.metadataTableSchemaComboBox.currentText())
        s.setValue("GeoCat/metadataTableName", self.metadataTableNameComboBox.currentText())
        s.setValue("GeoCat/titleColumn", self.titleColumnComboBox.currentText())
        s.setValue("GeoCat/abstractColumn", self.abstractColumnComboBox.currentText())
        s.setValue("GeoCat/gisLayerSchemaCol", self.layerSchemaNameComboBox.currentText())
        s.setValue("GeoCat/gisLayerTableCol", self.layerTableNameComboBox.currentText())
        s.setValue("GeoCat/gisLayerTypeCol", self.layerTypeComboBox.currentText())
        s.setValue("GeoCat/gisRasterPathCol", self.rasterPathComboBox.currentText())
        s.setValue("GeoCat/ignoreCol", self.ignoreComboBox.currentText())
        s.setValue("GeoCat/privateCol", self.privateComboBox.currentText())
        s.setValue("GeoCat/qgisConnectionCol", self.qgis_connection_cbo.currentText())
        s.setValue("GeoCat/vectorIdentifier", self.vectorIdentifierLineEdit.text())
        s.setValue("GeoCat/rasterIdentifier", self.rasterIdentifierLineEdit.text())
        s.setValue("GeoCat/wmsIdentifier", self.wmsIdentifierLineEdit.text())
        s.setValue("GeoCat/viewPrimaryKey", self.view_pk_le.text())
        self.set_custom_columns_settings()
        # Save the dialog width too
        s.setValue("GeoCat/settingsDialogWidth", self.width())

        self.accept()

    def block_widgets_signals(self, block=True, class_list=[]):
        for cl in class_list:
            for w in self.findChildren(cl):
                w.blockSignals(block)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
