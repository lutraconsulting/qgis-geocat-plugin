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

from psycopg2.extras import DictCursor
import traceback
import datetime
# noinspection PyPackageRequirements
from PyQt4.QtGui import (
    QDialog,
    QLabel,
    QLineEdit,
    QTextEdit,
    QDateEdit,
    QDesktopServices
)
from PyQt4.QtCore import Qt, QUrl, QSettings, QDate
from dbutils import (
    get_postgres_conn_info,
    get_connection
)
from qgis.core import (
    QgsDataSourceURI,
    QgsVectorLayer,
    QgsMapLayerRegistry,
    QgsMessageLog
)
from qgis.gui import QgsMessageBar
from .gc_utils import load_ui


FORM_CLASS = load_ui('geo_cat_dialog_base')


class GeoCatDialog(QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.iface = iface
        self.config = dict()
        self._setup_config()
        self.wclasses = {'QLineEdit': QLineEdit,
                         'QTextEdit': QTextEdit,
                         'QDateEdit': QDateEdit}
        # self.setup_custom_widgets()
        self.search_results = []

        # signals
        self.searchPushButton.clicked.connect(self.search)
        self.searchLineEdit.returnPressed.connect(self.search)
        self.resultsListWidget.doubleClicked.connect(self.add_selected_layers)
        self.resultsListWidget.currentRowChanged.connect(self.display_details)
        self.resultsListWidget.itemSelectionChanged.connect(self.on_result_sel_changed)
        self.helpPushButton.clicked.connect(self.show_help)
        self.closePushButton.clicked.connect(self.reject)
        self.addSelectedPushButton.clicked.connect(self.add_selected_layers)

    def setup_custom_widgets(self):
        # read custom columns settings
        self.clear_layout(self.customColsLayout)
        s = QSettings()
        s.beginGroup('GeoCat/CustomColumns')
        self.cust_cols = []
        for i, cc in enumerate(s.childGroups()):
            self.cust_cols.insert(i, {})
            s.beginGroup(cc)
            self.cust_cols[i]['desc'] = s.value('desc')
            self.cust_cols[i]['col'] = s.value('col')
            self.cust_cols[i]['widget'] = s.value('widget', 'QLineEdit')
            s.endGroup()

        # create widgets for custom columns
        for i, c in enumerate(self.cust_cols):
            col_name = c['col']
            label = QLabel(c['desc'])
            self.customColsLayout.addWidget(label)
            w = self.wclasses[c['widget']]()
            w.setObjectName('{}_{}'.format(col_name, i))
            w.setReadOnly(True)
            self.customColsLayout.addWidget(w)

    def _setup_config(self):
        s = QSettings()
        self.config['connection'] = s.value('GeoCat/connection', '', type=str)
        self.config['cat_schema'] = '"%s"' % s.value('GeoCat/metadataTableSchema', '', type=str)
        self.config['cat_table'] = '"%s"' % s.value('GeoCat/metadataTableName', '', type=str)
        self.config['title_col'] = '"%s"' % s.value('GeoCat/titleColumn', '', type=str)
        self.config['abstract_col'] = '"%s"' % s.value('GeoCat/abstractColumn', '', type=str)
        self.config['schema_col'] = '"%s"' % s.value('GeoCat/gisLayerSchemaCol', '', type=str)
        self.config['table_col'] = '"%s"' % s.value('GeoCat/gisLayerTableCol', '', type=str)

    def _db_cur(self):
        con_info = get_postgres_conn_info(self.config['connection'])
        if not self.config['connection']:
            return None
        con = get_connection(con_info)
        return con.cursor(cursor_factory=DictCursor)

    def show_help(self):
        help_url = 'http://intranet.dartmoor-npa.gov.uk/useful_i/gis-mapping-guidance'
        QDesktopServices.openUrl(QUrl(help_url))

    def search(self):
        """
            Takes the user input and searches the metadata table (name and abstract columns), returning
            results for display.  The following details are returned and stored:
                Title
                Abstract
                Date published
                Schema
                Table

        :return:
        """
        # import pydevd; pydevd.settrace('localhost', port=5678)

        cur = self._db_cur()
        if not cur:
            self.bar_warn('There is no connection defined.')
            return

        search_text = self.searchLineEdit.text()

        if search_text.strip() == '':
            self.search_results = []
            self.resultsListWidget.clear()
            self.clear_details()
            return

        wildcarded_search_string = ''
        for part in search_text.split():
            wildcarded_search_string += '%' + part
        wildcarded_search_string += '%'
        query_dict = {'search_text': wildcarded_search_string}

        # parts of the QUERY for custom columns
        cc_select = ''
        cc_where = ''
        for c in self.cust_cols:
            col_name = c['col']
            if not col_name:
                continue
            # check the column type
            if self.get_col_type(col_name) in ['date']:
                cc_select += ",\nto_char(cat.{}, 'YYYY-MM-DD') AS {}".format(col_name, col_name)
            else:
                cc_select += ',\ncat.{}'.format(col_name)
            cc_where += '\nOR cat.{}::text ILIKE %(search_text)s'.format(col_name)

        qry = """
            SELECT
                cat.""" + self.config['title_col'] + """,
                cat.""" + self.config['abstract_col'] + """,
                cat.""" + self.config['schema_col'] + """,
                cat.""" + self.config['table_col'] + """,
                gc.f_geometry_column,
                gc.type""" + cc_select + """
            FROM
                """ + self.config['cat_schema'] + """.""" + self.config['cat_table'] + """ AS cat,
                public.geometry_columns AS gc
            WHERE
                (
                    cat.""" + self.config['title_col'] + """ ILIKE %(search_text)s OR
                    cat.""" + self.config['abstract_col'] + """ ILIKE %(search_text)s
                    """ + cc_where + """
                ) AND
                cat.""" + self.config['schema_col'] + """ IS NOT NULL AND
                cat.""" + self.config['table_col'] + """ IS NOT NULL AND
                -- Join conditions:
                cat.""" + self.config['schema_col'] + """ = gc.f_table_schema AND
                cat.""" + self.config['table_col'] + """ = gc.f_table_name"""
        try:
            cur.execute(qry, query_dict)
        except Exception:
            self.bar_warn('Querying the metadata table failed! See logs and check your settings.')
            self.log_info(traceback.format_exc())
            self.search_results = []
            return

        # Clear the results
        self.search_results = []
        self.resultsListWidget.clear()

        for row in cur.fetchall():
            res = dict()
            title, abstract, schema, table, geom_col, ty = row[:6]
            for c in self.cust_cols:
                col_name = c['col']
                res[col_name] = row[col_name]
            if title is None:
                title = 'Untitled'
            res['title'] = title
            res['abstract'] = abstract
            # res['date'] = date
            res['schema'] = schema
            res['table'] = table
            res['geom_col'] = geom_col
            res['geom_type'] = ty
            self.search_results.append(res)
            display_geom = ty.lower()
            if display_geom.startswith('multi'):
                display_geom = display_geom[5:]
            self.resultsListWidget.addItem('%s (%s)' % (title, display_geom))

    def get_col_type(self, col_name):
        cur = self._db_cur()
        qry = '''SELECT data_type FROM information_schema.columns
                        WHERE table_schema = '{}' AND
                        table_name = '{}' AND
                        column_name = '{}';'''.format(
            self.config['cat_schema'].replace('\"', ''),
            self.config['cat_table'].replace('\"', ''),
            col_name
        )
        cur.execute(qry)
        return cur.fetchone()[0]

    def add_selected_layers(self):
        """
            Add each of the selected layers to QGIS.
        :return:
        """
        for i in range(self.resultsListWidget.count()):
            # Loop through and add selected items
            if self.resultsListWidget.item(i).isSelected():
                # Add the layer
                uri = QgsDataSourceURI()
                con_info = get_postgres_conn_info(self.config['connection'])
                uri.setConnection(con_info['host'],
                                  str(con_info['port']),
                                  con_info['database'],
                                  con_info['user'],
                                  con_info['password'])
                res = self.search_results[i]
                display_geom = res['geom_type'].lower()
                if display_geom.startswith('multi'):
                    display_geom = display_geom[5:]
                uri.setDataSource(res['schema'],
                                  res['table'],
                                  res['geom_col'])
                layer_name = '%s (%s)' % (res['title'], display_geom)
                vlayer = QgsVectorLayer(uri.uri(), layer_name, 'postgres')
                QgsMapLayerRegistry.instance().addMapLayer(vlayer)

    def display_details(self, current_row):
        """
            When a result is selected, display its details in the widgets to the right.

        :param current_row: The index of the selection
        :return:
        """
        if current_row < 0:
            return
        # required columns
        title = self.search_results[current_row]['title']
        self.title_ledit.setText(title)
        abstract = self.search_results[current_row]['abstract']
        self.abstract_ledit.setText(abstract)

        # custom columns
        for i, c in enumerate(self.cust_cols):
            col_name = c['col']
            wid = self.findChild(self.wclasses[c['widget']], '{}_{}'.format(col_name, i))
            val = self.search_results[current_row][col_name]
            if c['widget'] in ['QLineEdit', 'QTextEdit']:
                str_val = str(val)
                wid.setText(str_val)
            elif c['widget'] == 'QDateEdit':
                if isinstance(val, datetime.datetime):
                    val = val.strftime('%Y-%m-%d')
                date = QDate.fromString(val,Qt.ISODate)
                wid.setDate(date)

    def clear_details(self):
        # required columns
        self.title_ledit.clear()
        self.abstract_ledit.clear()

        # custom columns
        for i, c in enumerate(self.cust_cols):
            col_name = c['col']
            wid = self.findChild(self.wclasses[c['widget']], '{}_{}'.format(col_name, i))
            wid.clear()

    def on_result_sel_changed(self):
        # Determine if we have a selection, if so, enable the add features button
        if len(self.resultsListWidget.selectedItems()) > 0:
            self.addSelectedPushButton.setEnabled(True)
        else:
            self.addSelectedPushButton.setEnabled(False)

    def clear_layout(self, layout):
        for i in reversed(range(layout.count())):
            widgetToRemove = layout.itemAt(i).widget()
            # remove it from the layout list
            layout.removeWidget(widgetToRemove)
            # remove it from the gui
            widgetToRemove.setParent(None)

    def log_info(self, msg):
        try:
            QgsMessageLog.logMessage(msg, 'Layer Metadata Search', QgsMessageLog.INFO)
        except TypeError:
            QgsMessageLog.logMessage(repr(msg), 'Layer Metadata Search', QgsMessageLog.INFO)

    def bar_warn(self, msg, dur=5):
        self.iface.messageBar().pushMessage('Layer Metadata Search', msg, level=QgsMessageBar.WARNING, duration=dur)
