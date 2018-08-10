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

import datetime
import traceback
from qgis.core import (
    QgsDataSourceURI,
    QgsVectorLayer,
    QgsMapLayerRegistry
)

from PyQt4.QtCore import Qt, QUrl, QSettings, QDate, SIGNAL
# noinspection PyPackageRequirements
from PyQt4.QtGui import (
    QDialog,
    QLabel,
    QLineEdit,
    QTextEdit,
    QDateEdit,
    QDesktopServices,
    QStandardItemModel,
    QStandardItem,
    QAbstractItemView,
    QShortcut,
    QKeySequence)
from psycopg2.extras import DictCursor

from dbutils import (
    get_postgres_conn_info,
    get_connection,
    list_columns
)
from errors import CustomColumnException, ConnectionException
from user_communication import UserCommunication
from .gc_utils import load_ui

FORM_CLASS = load_ui('geo_cat_dialog_base')


class GeoCatDialog(QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        self.db_con = None
        QDialog.__init__(self, parent)
        self.setupUi(self)
        s = QSettings()
        is_maximised = s.value('GeoCat/searchDialogMaximised', False, type=bool)
        width = s.value('GeoCat/searchDialogWidth', 0, type=int)
        height = s.value('GeoCat/searchDialogHeight', 0, type=int)
        show_private_cs = s.value('GeoCat/showPrivate', 2, type=int)
        if is_maximised:
            self.showMaximized()
        elif width != 0 and height != 0:
            self.resize(width, height)
        self.iface = iface
        self.uc = UserCommunication(iface, 'Metadata Plugin')
        self.config = dict()
        self._setup_config()
        self.wclasses = {'QLineEdit': QLineEdit,
                         'QTextEdit': QTextEdit,
                         'QDateEdit': QDateEdit}
        self.search_results = []
        self.tableToResults = {}
        self.cust_cols = None
        self.meta_cols = None

        self.table_model = QStandardItemModel()
        self.init_table()

        self.showPrivateCheckBox.setCheckState(show_private_cs)

        # signals
        self.searchPushButton.clicked.connect(self.search_push_button_clicked)
        self.searchLineEdit.returnPressed.connect(self.search)
        self.showPrivateCheckBox.stateChanged.connect(self.show_private_check_box_toggled)

        self.resultsTable.doubleClicked.connect(self.add_selected_layers)

        self.resultsTable.selectionModel().selectionChanged.connect(self.display_details_table)
        self.resultsTable.selectionModel().selectionChanged.connect(self.on_result_sel_changed)

        self.helpPushButton.clicked.connect(self.show_help)
        self.closePushButton.clicked.connect(self.on_close_clicked)
        self.addSelectedPushButton.clicked.connect(self.add_selected_layers)

        self.browseAllCheckBox.stateChanged.connect(self.browse_all_check_box_toggled)

        # Keyboard shortcut to focus and highlight search text
        self.connect(QShortcut(QKeySequence(Qt.CTRL + Qt.Key_F), self), SIGNAL('activated()'), self.ctrl_f_pressed)

        # import pydevd; pydevd.settrace(suspend=False)

    def search_push_button_clicked(self, checked):
        self.search()

    def show_private_check_box_toggled(self, check_state):
        self.search()

    def browse_all_check_box_toggled(self, check_state):
        if check_state == Qt.Checked:
            self.searchGroupBox.setEnabled(False)
            self.search(use_where_clause=False)
        else:
            self.searchGroupBox.setEnabled(True)
            self.clear_results()
            self.ctrl_f_pressed()

    def ctrl_f_pressed(self):
        self.searchLineEdit.setFocus()
        self.searchLineEdit.selectAll()

    def setup_custom_widgets(self):
        self.clear_layout(self.customColsLayout)
        # read custom columns settings
        s = QSettings()
        s.beginGroup('GeoCat/CustomColumns')
        self.cust_cols = []
        for i, cc in enumerate(sorted(s.childGroups(), key=int)):
            self.cust_cols.insert(i, {})
            s.beginGroup(cc)
            self.cust_cols[i]['desc'] = s.value('desc')
            self.cust_cols[i]['col'] = s.value('col')
            self.cust_cols[i]['widget'] = s.value('widget', 'QLineEdit')
            s.endGroup()

        # create widgets for custom columns
        cur = self._db_cur(dict=False)
        if not cur:
            raise ConnectionException
        cols = list_columns(cur,
                            (self.config['cat_schema']).strip('"'),
                            (self.config['cat_table']).strip('"')
        )
        for i, c in enumerate(self.cust_cols):
            if not c['col'] in cols:
                raise CustomColumnException('Metadata table has no "{}" column. Check your settings.'.format(c['col']))
            if not c['desc']:
                raise CustomColumnException('Custom column has no description. Check your settings.')
            label = QLabel(c['desc'])
            self.customColsLayout.addWidget(label)
            w = self.wclasses[c['widget']]()
            w.setObjectName('{}_{}'.format(c['col'], i))
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
        self.config['type_col'] = '"%s"' % s.value('GeoCat/gisLayerTypeCol', '', type=str)
        self.config['rpath_col'] = '"%s"' % s.value('GeoCat/gisRasterPathCol', '', type=str)
        self.config['ignore_col'] = '"%s"' % s.value('GeoCat/ignoreCol', '', type=str)
        self.config['private_col'] = '"%s"' % s.value('GeoCat/privateCol', '', type=str)
        self.config['vector_identifier'] = s.value('GeoCat/vectorIdentifier', 'vector', type=str)
        self.config['raster_identifier'] = s.value('GeoCat/rasterIdentifier', 'raster', type=str)
        self.config['wms_identifier'] = s.value('GeoCat/wmsIdentifier', 'wms', type=str)

    def _db_cur(self, dict=True):
        con_info = get_postgres_conn_info(self.config['connection'])
        if not self.config['connection']:
            return None
        if self.db_con is None or self.db_con.closed != 0:
            # Get a connection if we do not already have one or if it's been closed
            self.db_con = get_connection(con_info)
        if dict:
            return self.db_con.cursor(cursor_factory=DictCursor)
        else:
            return self.db_con.cursor()

    def show_help(self):
        help_url = 'https://github.com/lutraconsulting/qgis-geocat-plugin'
        QDesktopServices.openUrl(QUrl(help_url))

    def get_metadata_table_cols(self, cur):
        qry = "SELECT column_name FROM information_schema.columns "+ \
                      "WHERE table_schema = {} AND table_name = {}".format(self.config['cat_schema'], self.config['cat_table']).replace('\"', '\'')
        try:
            cur.execute(qry)

            return cur.fetchall()
        except Exception:
            self.uc.bar_warn('Querying the metadata table failed! See logs and check your settings.')
            self.uc.log_info(traceback.format_exc())
            self.search_results = []
            return

    def search(self, use_where_clause=True):
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
        cur = self._db_cur()
        if not cur:
            self.uc.bar_warn('There is no connection defined.')
            return

        search_text = self.searchLineEdit.text()

        if search_text.strip() == '':
            self.clear_results()
            if use_where_clause:
                return

        wildcarded_search_string = ''
        for part in search_text.split():
            wildcarded_search_string += '%' + part
        wildcarded_search_string += '%'
        query_dict = {'search_text': wildcarded_search_string,
                      'vector_identifier': self.config['vector_identifier'],
                      'raster_identifier': self.config['raster_identifier'],
                      'wms_identifier': self.config['wms_identifier']}

        # parts of the QUERY for custom columns
        cc_select = ''
        cc_where = ''
        for c in self.cust_cols:
            col_name = c['col']
            if not col_name:
                continue
            # check the column type
            if self.get_col_type(col_name) in ['date']:
                cc_select += ",\nto_char(cat.{}, 'DD/MM/YY') AS {}".format(col_name, col_name)
            else:
                cc_select += ',\ncat.{}'.format(col_name)
            cc_where += '\nOR cat.{}::text ILIKE %(search_text)s'.format(col_name)

        meta_select = ''
        meta_where = ''
        ignore_list = [self.config['ignore_col'].strip('"'),
                       'id',
                       self.config['private_col'].strip('"'),
                       self.config['type_col'].strip('"'),
                       self.config['rpath_col'].strip('"')]
        # TODO clean up redundant cols in query
        self.meta_cols = self.get_metadata_table_cols(cur)
        for col in self.meta_cols:
            if not col:
                continue
            col_name = col[0]
            if not col_name or col_name in ignore_list:
                continue
            # check the column type
            if self.get_col_type(col_name) in ['date']:
                meta_select += ",\nto_char(cat.{}, 'DD/MM/YY') AS {}".format(col_name, col_name)
            else:
                meta_select += ',\ncat.{}'.format(col_name)
            meta_where += '\nOR cat.{}::text ILIKE %(search_text)s'.format(col_name)

        private_select = ', FALSE AS private'
        if self.config['private_col'] != '""' and self.config['private_col'] != '"--DISABLED--"':
            private_select = ', ' + self.config['private_col'] + ' AS private'

        qry_where = """"""
        if use_where_clause:
            qry_where = """(
                                cat.""" + self.config['title_col'] + """ ILIKE %(search_text)s OR
                                cat.""" + self.config['abstract_col'] + """ ILIKE %(search_text)s
                                """ + cc_where + """
                                """ + meta_where + """
                            ) AND """
        qry = """
            SELECT
                cat.""" + self.config['title_col'] + """,
                cat.""" + self.config['abstract_col'] + """,
                cat.""" + self.config['schema_col'] + """,
                cat.""" + self.config['table_col'] + """,
                gc.f_geometry_column,
                gc.type""" + private_select + cc_select + """
                """ + meta_select + """
            FROM
                """ + self.config['cat_schema'] + """.""" + self.config['cat_table'] + """ AS cat,
                public.geometry_columns AS gc
            WHERE
				gc.f_table_schema = cat.""" + self.config['schema_col'] + """ AND
				gc.f_table_name = cat.""" + self.config['table_col'] + """ AND
                """ + qry_where + """
                cat.""" + self.config['ignore_col'] + """ != TRUE AND
                cat.""" + self.config['type_col'] + """ = %(vector_identifier)s
                """
        if self.showPrivateCheckBox.checkState() == Qt.Unchecked and use_where_clause:
            qry += """ AND """ + self.config['private_col'] + """ = FALSE"""
        try:
            cur.execute(qry, query_dict)
        except Exception:
            self.uc.bar_warn('Querying the metadata table failed! See logs and check your settings.')
            self.uc.log_info(traceback.format_exc())
            self.search_results = []
            return

        self.clear_results()

        for row in cur.fetchall():
            res = dict()
            title, abstract, schema, table, geom_col, ty, private = row[:7]
            for c in self.cust_cols:
                col_name = c['col']
                res[col_name] = row[col_name]
            res['type'] = 'vector'
            res['title'] = title
            res['abstract'] = abstract
            res['schema'] = schema
            res['table'] = table
            res['rpath'] = None
            res['geom_col'] = geom_col
            res['geom_type'] = ty
            if private:
                res['private'] = 'Yes'
            else:
                res['private'] = 'No'
            # Replace None types with '' for better usability
            for k in res.keys():
                if res[k] is None: res[k] = ''
            self.search_results.append(res)

        # search rasters and WMS
        qry_where = """"""
        if use_where_clause:
            qry_where = """ AND (
                                cat.""" + self.config['title_col'] + """ ILIKE %(search_text)s OR
                                cat.""" + self.config['abstract_col'] + """ ILIKE %(search_text)s
                                """ + cc_where + """
                            )"""
        qry = """
                    SELECT
                        cat.""" + self.config['title_col'] + """,
                        cat.""" + self.config['abstract_col'] + """,
                        cat.""" + self.config['rpath_col'] + """,
                        CASE WHEN cat.""" + self.config['type_col'] + """ = %(raster_identifier)s THEN
                            'raster'
                        ELSE
                            'wms'
                        END AS type""" + private_select + cc_select + """
                    FROM
                        """ + self.config['cat_schema'] + """.""" + self.config['cat_table'] + """ AS cat
                    WHERE
                        (
                            cat.""" + self.config['type_col'] + """ = %(raster_identifier)s OR
                            cat.""" + self.config['type_col'] + """ = %(wms_identifier)s
                        ) AND
                        cat.""" + self.config['ignore_col'] + """ != TRUE
                    """ + qry_where
        if self.showPrivateCheckBox.checkState() == Qt.Unchecked and use_where_clause:
            qry += """ AND """ + self.config['private_col'] + """ = FALSE"""
        try:
            cur.execute(qry, query_dict)
        except Exception:
            self.uc.bar_warn('Querying the metadata table for rasters failed! See logs and check your settings.')
            self.uc.log_info(traceback.format_exc())
            return

        for row in cur.fetchall():
            res = dict()
            title, abstract, rpath, subtype, private = row[:5]
            for c in self.cust_cols:
                col_name = c['col']
                res[col_name] = row[col_name]
            res['type'] = subtype
            res['title'] = title
            res['abstract'] = abstract
            res['rpath'] = rpath
            res['geom_col'] = 'N/A'
            res['geom_type'] = 'N/A'
            res['schema'] = 'N/A'
            res['table'] = 'N/A'
            if private:
                res['private'] = 'Yes'
            else:
                res['private'] = 'No'
            # Replace None types with '' for better usability
            for k in res.keys():
                if res[k] is None: res[k] = ''
            self.search_results.append(res)

        self.appendToResultTable(include_private=self.showPrivateCheckBox.checkState())

    def clear_results(self):
        self.search_results = []
        self.tableToResults = {}
        self.table_model.clear()
        self.clear_details()

    def init_table(self):
        self.resultsTable.setModel(self.table_model)
        self.resultsTable.setSortingEnabled(True)
        self.table_model.clear()
        self.resultsTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.resultsTable.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def appendToResultTable(self, include_private=True):
        # Header
        if len(self.search_results):
            # Type
            labels = ['Type']
            # Mandatory informative columns
            labels.extend(['Title', 'Abstract'])
            # Custom columns
            for cc in self.cust_cols:
                labels.append(cc['desc'])
            # Other information
            labels.extend(['Restricted?', 'Schema', 'Table', 'Path'])
            self.table_model.setHorizontalHeaderLabels(labels)
            self.resultsTable.resizeColumnsToContents()

        # Content
        for row, item in enumerate(self.search_results):

            row_items = []

            # Type column
            item_text = 'UNDEFINED'
            if item['type'] == 'vector':
                display_geom = item['geom_type'].lower()
                if 'multi' in display_geom:
                    display_geom = display_geom[5:]
                item_text = 'Vector %s' % display_geom
            elif item['type'] == 'raster':
                item_text = 'Raster'
            elif item['type'] == 'wms':
                item_text = 'WMS'
            new_item = QStandardItem(item_text)
            row_items.append(new_item)

            # Title and abstract
            new_item = QStandardItem(item['title'])
            row_items.append(new_item)
            new_item = QStandardItem(item['abstract'])
            row_items.append(new_item)

            # Custom columns
            for cc in self.cust_cols:
                new_item = QStandardItem(item[cc['col']])
                row_items.append(new_item)

            # Other information
            new_item = QStandardItem(item['private'])
            row_items.append(new_item)
            new_item = QStandardItem(item['schema'])
            row_items.append(new_item)
            new_item = QStandardItem(item['table'])
            row_items.append(new_item)
            r_path_text = item['rpath']
            if r_path_text is None:
                r_path_text = 'N/A'
            new_item = QStandardItem(r_path_text)
            row_items.append(new_item)

            self.table_model.appendRow(row_items)
            item = self.table_model.item(row)
            self.tableToResults[item] = row

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

        selection = self.resultsTable.selectionModel().selectedRows()
        for i in range(len(selection)):
            index = selection[i]
            item = self.table_model.item(index.row())
            ix = self.tableToResults[item]
            res = self.search_results[ix]
            if res['type'] == 'vector':
                # Add the vector layer
                uri = QgsDataSourceURI()
                con_info = get_postgres_conn_info(self.config['connection'])
                uri.setConnection(con_info['host'],
                                  str(con_info['port']),
                                  con_info['database'],
                                  con_info.get('user', None),
                                  con_info.get('password', None))

                display_geom = res['geom_type'].lower()
                if display_geom.startswith('multi'):
                    display_geom = display_geom[5:]
                uri.setDataSource(res['schema'],
                                  res['table'],
                                  res['geom_col'])
                layer_title = res['title']
                if layer_title is None or layer_title == '':
                    layer_title = res['table']
                layer_name = '%s (%s)' % (layer_title, display_geom)
                vlayer = QgsVectorLayer(uri.uri(), layer_name, 'postgres')
                if vlayer.isValid():
                    QgsMapLayerRegistry.instance().addMapLayer(vlayer)
                else:
                    self.uc.bar_warn('{} is not a valid vector layer.')
                    self.uc.log_info('{} is not a valid vector layer\n{}'.format(
                        res['title'], res))
            else:
                # Add the raster layer
                layer_name = '{} (raster)'.format(res['title'])
                self.iface.addRasterLayer(res['rpath'], layer_name)

    def display_details_table(self):
        selected_rows  = self.resultsTable.selectionModel().selectedRows()
        if len(selected_rows):
            index = selected_rows[0]
            item = self.table_model.item(index.row())
            ix = self.tableToResults[item]
            self.display_details(ix)


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
        if len(self.resultsTable.selectionModel().selectedRows()) > 0:
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

    def on_close_clicked(self):
        s = QSettings()
        s.setValue("GeoCat/searchDialogMaximised", self.isMaximized())
        s.setValue("GeoCat/searchDialogWidth", self.width())
        s.setValue("GeoCat/searchDialogHeight", self.height())
        s.setValue("GeoCat/showPrivate", self.showPrivateCheckBox.checkState())
        self.reject()