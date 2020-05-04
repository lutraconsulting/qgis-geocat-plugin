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
from operator import itemgetter
from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsDataSourceUri,
    QgsRasterLayer
)

from qgis.PyQt.QtCore import Qt, QUrl, QSettings, QDate, QSortFilterProxyModel
# noinspection PyPackageRequirements
from qgis.PyQt.QtWidgets import QDialog, QLabel, QLineEdit, QTextEdit, QDateEdit, QAbstractItemView, QShortcut
from qgis.PyQt.QtGui import QDesktopServices, QStandardItemModel, QStandardItem, QKeySequence
from psycopg2.extras import DictCursor

from .dbutils import (
    get_postgres_conn_info_and_meta,
    get_connection,
    list_columns,
    get_first_column
)
from .errors import CustomColumnException, ConnectionException
from .user_communication import UserCommunication
from .gc_utils import load_ui

FORM_CLASS = load_ui('geo_cat_dialog_base')


class GeoCatDialog(QDialog, FORM_CLASS):
    COLUMNS_DEFAULTS = {
            'table': {'label': 'Table', 'idx': 0, 'vidx': 0, 'width': None},
            'schema': {'label': 'Schema', 'idx': 1, 'vidx': 1, 'width': None},
            'title': {'label': 'Title', 'idx': 2, 'vidx': 2, 'width': None},
            'abstract': {'label': 'Abstract', 'idx': 3, 'vidx': 3, 'width': None},
            'type': {'label': 'Type', 'idx': 4, 'vidx': 4, 'width': None},
            'private': {'label': 'Restricted?', 'idx': 5, 'vidx': 5, 'width': None},
            'rpath': {'label': 'Path', 'idx': 6, 'vidx':6, 'width': None},
            'qgis_connection': {'label': 'QGIS PG Connection', 'idx': 7, 'vidx': 7, 'width': None}
        }

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
        self.columns_specification = dict()
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
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.resultsTable.setSortingEnabled(True)
        self.horizontal_header = self.resultsTable.horizontalHeader()
        self.init_table()

        self.showPrivateCheckBox.setCheckState(show_private_cs)

        # signals
        self.searchPushButton.clicked.connect(self.search_push_button_clicked)
        self.searchLineEdit.returnPressed.connect(self.search)
        self.showPrivateCheckBox.stateChanged.connect(self.show_private_check_box_toggled)

        self.resultsTable.doubleClicked.connect(self.add_selected_layers)

        self.resultsTable.selectionModel().selectionChanged.connect(self.display_details_table)
        self.resultsTable.selectionModel().selectionChanged.connect(self.on_result_sel_changed)
        self.horizontal_header.sectionMoved.connect(self.on_column_moved)
        self.horizontal_header.sectionResized.connect(self.on_column_resized)
        self.helpPushButton.clicked.connect(self.show_help)
        self.closePushButton.clicked.connect(self.on_close_clicked)
        self.addSelectedPushButton.clicked.connect(self.add_selected_layers)

        self.browseAllCheckBox.stateChanged.connect(self.browse_all_check_box_toggled)

        # Keyboard shortcut to focus and highlight search text
        self.search_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_F), self)
        self.search_shortcut.activated.connect(self.ctrl_f_pressed)

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
        self.config['qgis_connection_col'] = '"%s"' % s.value('GeoCat/qgisConnectionCol', '', type=str)
        self.config['vector_identifier'] = s.value('GeoCat/vectorIdentifier', 'vector', type=str)
        self.config['raster_identifier'] = s.value('GeoCat/rasterIdentifier', 'raster', type=str)
        self.config['wms_identifier'] = s.value('GeoCat/wmsIdentifier', 'wms', type=str)

    def _db_cur(self, dict=True):
        con_info, con_meta = get_postgres_conn_info_and_meta(self.config['connection'])
        if not self.config['connection']:
            return None
        if self.db_con is None or self.db_con.closed != 0:
            # Get a connection if we do not already have one or if it's been closed
            self.db_con = get_connection(con_info)
            # make sure connection could be created
            if not self.db_con:
                return
        if self.db_con:
            if dict:
                return self.db_con.cursor(cursor_factory=DictCursor)
            else:
                return self.db_con.cursor()

    def show_help(self):
        help_url = 'https://github.com/lutraconsulting/qgis-geocat-plugin'
        QDesktopServices.openUrl(QUrl(help_url))

    def get_metadata_table_cols(self, cur):
        qry = "SELECT column_name FROM information_schema.columns " + \
                      "WHERE table_schema = {} AND table_name = {}".format(self.config['cat_schema'], self.config['cat_table']).replace('\"', '\'')
        try:
            cur.execute(qry)

            return cur.fetchall()
        except Exception:
            self.uc.bar_warn('Querying the metadata table failed! See logs and check your settings.')
            self.uc.log_info(traceback.format_exc())
            self.search_results = []
            return

    def process_search_text(self, search_text):
        wildcarded_search_string = ''
        for part in search_text.split():
            wildcarded_search_string += '%' + part
        wildcarded_search_string += '%'
        query_dict = {'search_text': wildcarded_search_string,
                      'vector_identifier': self.config['vector_identifier'],
                      'raster_identifier': self.config['raster_identifier'],
                      'wms_identifier': self.config['wms_identifier']}
        return query_dict

    def vector_query(self, cur, use_where_clause):
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

        qgis_connection_select = ', NULL AS qgis_connection'
        if self.config['qgis_connection_col'] != '""' and self.config['qgis_connection_col'] != '"--DISABLED--"':
            qgis_connection_select = ', ' + self.config['qgis_connection_col'] + ' AS qgis_connection'

        ignore_clause = 'TRUE'
        if self.config['ignore_col'] != '""' and self.config['ignore_col'] != '"--DISABLED--"':
            ignore_clause = """ cat.""" + self.config['ignore_col'] + """ != TRUE"""

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
                        cat.""" + self.config['table_col'] + """
                        """ + private_select + qgis_connection_select + cc_select + """
                        """ + meta_select + """
                    FROM
                        """ + self.config['cat_schema'] + """.""" + self.config['cat_table'] + """ AS cat
                    WHERE
                        """ + qry_where + ignore_clause + """ AND
                        cat.""" + self.config['type_col'] + """ = %(vector_identifier)s
                        """
        if self.showPrivateCheckBox.checkState() == Qt.Unchecked and use_where_clause and self.config['private_col'] != '"--DISABLED--"':
            qry += """ AND """ + self.config['private_col'] + """ = FALSE"""

        return qry, cc_select, cc_where, private_select, ignore_clause

    def raster_query(self, cc_select, cc_where, private_select, ignore_clause, use_where_clause):
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
                                """ + ignore_clause + """
                            """ + qry_where
        if self.showPrivateCheckBox.checkState() == Qt.Unchecked and use_where_clause and self.config['private_col'] != '"--DISABLED--"':
            qry += """ AND """ + self.config['private_col'] + """ = FALSE"""

        return qry

    def find_geom_and_type(self, table_schema, table_name, qgis_connection):
        qry = """
        SELECT 
            gc.f_geometry_column,
            gc.type
        FROM
            public.geometry_columns AS gc
        WHERE
            gc.f_table_schema = '{}' AND
            gc.f_table_name = '{}'
        """.format(table_schema, table_name)

        if not qgis_connection:
            cur = self._db_cur(dict=False)
        else:
            con_info, con_meta = get_postgres_conn_info_and_meta(qgis_connection)
            if con_info:
                db_con = get_connection(con_info)
            else:
                raise ConnectionException('Connection details missing.')
            if db_con:
                cur = db_con.cursor()
            else:
                raise ConnectionException('Connection to DB failed.')
        cur.execute(qry)
        geom_and_type = cur.fetchone()
        if not geom_and_type:
            geom_and_type = (None, None)
        return geom_and_type

    def search(self, use_where_clause=True):
        """
        Takes the user input and searches the metadata table (name and abstract columns), returning
        results for display. The following details are returned and stored:
        Title
        Abstract
        Date published
        Schema
        Table
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

        query_dict = self.process_search_text(search_text)

        # search vectors
        vector_qry, cc_select, cc_where, private_select, ignore_clause = self.vector_query(cur, use_where_clause)
        try:
            cur.execute(vector_qry, query_dict)
        except Exception:
            self.uc.bar_warn('Querying the metadata table failed! See logs and check your settings.')
            self.uc.log_info(traceback.format_exc())
            self.search_results = []
            return

        self.clear_results()
        vector_results = cur.fetchall()

        # search rasters and WMS
        raster_qry = self.raster_query(cc_select, cc_where, private_select, ignore_clause, use_where_clause)
        try:
            cur.execute(raster_qry, query_dict)
        except Exception:
            self.uc.bar_warn('Querying the metadata table for rasters failed! See logs and check your settings.')
            self.uc.log_info(traceback.format_exc())
            return

        raster_results = cur.fetchall()

        for row in vector_results:
            res = dict()
            title, abstract, schema, table, private, qgis_con = row[:6]
            try:
                geom_col, ty = self.find_geom_and_type(schema, table, qgis_con)
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
                res['qgis_connection'] = qgis_con
                # Replace None types with '' for better usability
                for k in list(res.keys()):
                    if res[k] is None:
                        res[k] = ''
                self.search_results.append(res)
            except ConnectionException as e:
                self.uc.bar_warn(str(e) + ' Check the log.')
                self.uc.log_info('Failed to fetch item for {}.{} in {}.'.format(schema, table, qgis_con))

        for row in raster_results:
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
            res['qgis_connection'] = 'N/A'
            if private:
                res['private'] = 'Yes'
            else:
                res['private'] = 'No'
            # Replace None types with '' for better usability
            for k in list(res.keys()):
                if res[k] is None:
                    res[k] = ''
            self.search_results.append(res)

        self.appendToResultTable(include_private=self.showPrivateCheckBox.checkState())

    def clear_results(self):
        self.search_results = []
        self.tableToResults = {}
        self.table_model.clear()
        self.clear_details()

    def init_table(self):
        self.resultsTable.setModel(self.proxy_model)
        self.table_model.clear()
        self.resultsTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.resultsTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.horizontal_header.setSectionsMovable(True)

    def on_column_resized(self, log_idx, old_size, new_size):
        """Modifying columns specification during columns resizing."""
        idx_column = {value['idx']: key for key, value in list(self.columns_specification.items())}
        column = idx_column[log_idx]
        self.columns_specification[column]['width'] = new_size

        s = QSettings()
        s.setValue('GeoCat/columns_specification', self.columns_specification)

    def on_column_moved(self, log_idx, old_vidx, new_vidx):
        """Modifying columns specification during columns reordering."""
        idx_column = {value['idx']: key for key, value in list(self.columns_specification.items())}
        for visual_idx in range(self.horizontal_header.count()):
            logical_idx = self.horizontal_header.logicalIndex(visual_idx)
            column = idx_column[logical_idx]
            self.columns_specification[column]['vidx'] = visual_idx

        s = QSettings()
        s.setValue('GeoCat/columns_specification', self.columns_specification)

    def reorder_if_needed(self):
        """Replacing logical indexes with visual indexes if values differ each other."""
        s = QSettings()
        refresh_settings = False
        self.columns_specification = s.value('GeoCat/columns_specification')
        if not self.columns_specification or not set(self.COLUMNS_DEFAULTS.keys()).issubset(
                set(self.columns_specification.keys())):
            self.columns_specification = self.COLUMNS_DEFAULTS
        for k in list(self.columns_specification.keys()):
            idx = self.columns_specification[k]['idx']
            vidx = self.columns_specification[k]['vidx']
            if idx != vidx:
                self.columns_specification[k]['idx'] = vidx
                refresh_settings = True
        if refresh_settings is True:
            s.setValue('GeoCat/columns_specification', self.columns_specification)

    def read_columns_specification(self):
        """Reading columns specification from QSettings"""
        self.reorder_if_needed()
        s = QSettings()
        self.columns_specification = s.value('GeoCat/columns_specification')
        if not self.columns_specification or not set(self.COLUMNS_DEFAULTS.keys()).issubset(
                set(self.columns_specification.keys())):
            self.columns_specification = self.COLUMNS_DEFAULTS
        last_idx = max(val['idx'] for val in list(self.columns_specification.values()))
        for cc in self.cust_cols:
            column = cc['col']
            if column in self.columns_specification:
                continue
            label = cc['desc']
            last_idx += 1
            self.columns_specification[column] = {'label': label, 'idx': last_idx, 'vidx': last_idx, 'width': None}

    def appendToResultTable(self, include_private=True):
        # Header
        if len(self.search_results):
            self.read_columns_specification()
            labels = [val['label'] for val in sorted(list(self.columns_specification.values()), key=itemgetter('idx'))]
            self.table_model.setHorizontalHeaderLabels(labels)
            for val in list(self.columns_specification.values()):
                col_width = val['width']
                if col_width is not None:
                    self.horizontal_header.resizeSection(val['idx'], col_width)

        # Content
        sorted_spec = sorted(list(self.columns_specification.items()), key=lambda i: i[1]['idx'])
        for row, item in enumerate(self.search_results):
            row_items = []
            for k, v in sorted_spec:
                if k == 'type':
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
                elif k == 'rpath':
                    r_path_text = item[k]
                    if r_path_text is None:
                        r_path_text = 'N/A'
                    new_item = QStandardItem(r_path_text)
                else:
                    new_item = QStandardItem(item[k])
                row_items.append(new_item)

            self.table_model.appendRow(row_items)
            item = self.table_model.item(row)
            self.tableToResults[item.index()] = row

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
        """Add each of the selected layers to QGIS."""
        s = QSettings()
        view_pks = s.value('GeoCat/viewPrimaryKeys', '', type=str)
        view_pks = [pk.strip() for pk in view_pks.strip().split(',') if pk.strip()]
        selection = self.resultsTable.selectionModel().selectedRows()
        for i in range(len(selection)):
            proxy_index = selection[i]
            index = self.proxy_model.mapToSource(proxy_index)
            item = self.table_model.item(index.row())
            ix = self.tableToResults[item.index()]
            res = self.search_results[ix]

            if res['type'] == 'vector':
                # Add the vector layer
                qgis_connection = res['qgis_connection']
                uri = QgsDataSourceUri()
                if qgis_connection:
                    con_info, con_meta = get_postgres_conn_info_and_meta(qgis_connection)
                else:
                    con_info, con_meta = get_postgres_conn_info_and_meta(self.config['connection'])
                uri.setConnection(con_info['host'],
                                  str(con_info['port']),
                                  con_info['database'],
                                  con_info.get('user', None),
                                  con_info.get('password', None))
                # Set useEstimatedMetadata based on database connection settings
                if con_meta["estimated_metadata"]:
                    uri.setUseEstimatedMetadata(True)
                    if uri.hasParam('checkPrimaryKeyUnicity'):
                        uri.removeParam('checkPrimaryKeyUnicity')
                    uri.setParam('checkPrimaryKeyUnicity', '0')

                display_geom = res['geom_type'].lower()
                if display_geom.startswith('multi'):
                    display_geom = display_geom[5:]
                uri.setDataSource(res['schema'],
                                  res['table'],
                                  res['geom_col'])
                layer_title = res['title']
                if layer_title is None or layer_title == '':
                    layer_title = res['table']
                layer_name = '{} ({})'.format(layer_title, display_geom)

                vlayer = QgsVectorLayer(uri.uri(), layer_name, 'postgres')
                if vlayer.isValid():
                    QgsProject.instance().addMapLayer(vlayer)
                else:
                    try:
                        vlayer, pk = self.layer_from_view(layer_name, uri, view_pks)
                        if vlayer and vlayer.isValid():
                            QgsProject.instance().addMapLayer(vlayer)
                        else:
                            self.uc.bar_warn('\'{}\' table is not a valid vector layer.'.format(res['table']))
                            self.uc.log_info(
                                '\'{}\' table is not a valid vector layer\n{}\n View PK column: \'{}\''.format(
                                    res['table'], res, pk))
                    except IndexError:
                        self.uc.bar_warn('\'{}\' table can not be loaded.'.format(res['table']))
                        self.uc.log_info('\'{}\' table can not be loaded, check connection details'.format(res['table']))
            elif res['type'] == 'raster':
                layer_name = '{} (raster)'.format(res['title'])
                self.iface.addRasterLayer(res['rpath'], layer_name)
            elif res['type'] == 'wms':
                layer_name = '{} (raster)'.format(res['title'])
                wms_layer = QgsRasterLayer(res['rpath'], layer_name, 'wms')
                if wms_layer.isValid():
                    QgsProject.instance().addMapLayer(wms_layer)
                else:
                    self.uc.bar_warn('Raster layer \'{}\' could not be loaded.'.format(res['title']))
                    self.uc.log_info('Raster layer (\'{}\') could not be loaded. Its source is {}'.format(res['title'],res['rpath']))

    def layer_from_view(self, layer_name, uri, view_pks):
        pkeys = view_pks[:]
        try:
            pk = get_first_column(self._db_cur(), uri.schema(), uri.table())
        except IndexError:
            raise
        pkeys.append(pk)

        vlayer, last_pk = None, None
        for pkey in pkeys:
            last_pk = pkey
            uri.setKeyColumn(pkey)
            vlayer = QgsVectorLayer(uri.uri(), layer_name, 'postgres')
            if vlayer.isValid():
                break

        return vlayer, last_pk

    def display_details_table(self):
        selected_rows = self.resultsTable.selectionModel().selectedRows()
        if len(selected_rows):
            proxy_index = selected_rows[0]
            index = self.proxy_model.mapToSource(proxy_index)
            item = self.table_model.item(index.row())
            ix = self.tableToResults[item.index()]
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
                date = QDate.fromString(val, Qt.ISODate)
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

    @staticmethod
    def clear_layout(layout):
        for i in reversed(list(range(layout.count()))):
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
        s.setValue('GeoCat/columns_specification', self.columns_specification)
        self.reject()
