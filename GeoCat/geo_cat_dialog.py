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
    get_postgres_conn_info,
    get_connection
)

from qgis.core import (
    QgsDataSourceURI,
    QgsVectorLayer,
    QgsMapLayerRegistry
)

#FORM_CLASS, _ = uic.loadUiType(os.path.join(
#    os.path.dirname(__file__), 'geo_cat_dialog_base.ui'))
from geo_cat_dialog_base import Ui_GeoCatDialogBase


class GeoCatDialog(QtGui.QDialog, Ui_GeoCatDialogBase):
    def __init__(self, parent=None):
        """Constructor."""
        super(GeoCatDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.config = dict()
        self._setup_config()
        self.search_results = []

    def _setup_config(self):
        s = QSettings()
        self.config['connection'] = s.value('GeoCat/connection', '', type=str)
        self.config['cat_schema'] = '"%s"' % s.value('GeoCat/metadataTableSchema', '', type=str)
        self.config['cat_table'] = '"%s"' % s.value('GeoCat/metadataTableName', '', type=str)
        self.config['title_col'] = '"%s"' % s.value('GeoCat/titleColumn', '', type=str)
        self.config['abstract_col'] = '"%s"' % s.value('GeoCat/abstractColumn', '', type=str)
        self.config['date_col'] = '"date_published"'  # TODO
        self.config['schema_col'] = '"%s"' % s.value('GeoCat/gisLayerSchemaCol', '', type=str)
        self.config['table_col'] = '"%s"' % s.value('GeoCat/gisLayerTableCol', '', type=str)

    def _db_cur(self):
        con_info = get_postgres_conn_info(self.config['connection'])
        con = get_connection(con_info)
        return con.cursor()

    def show_help(self):
        help_url = 'http://intranet.dartmoor-npa.gov.uk/useful_i/gis-mapping-guidance'
        QtGui.QDesktopServices.openUrl(QUrl(help_url))

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

        search_text = self.searchLineEdit.text()

        wildcarded_search_string = ''
        for part in search_text.split():
            wildcarded_search_string += '%' + part
        wildcarded_search_string += '%'
        query_dict = {'search_text': wildcarded_search_string}

        cur.execute(""" SELECT
                            cat.""" + self.config['title_col'] + """,
                            cat.""" + self.config['abstract_col'] + """,
                            -- cat.""" + self.config['date_col'] + """,
                            cat.""" + self.config['schema_col'] + """,
                            cat.""" + self.config['table_col'] + """,
                            gc.f_geometry_column,
                            gc.type
                        FROM
                            """ + self.config['cat_schema'] + """.""" + self.config['cat_table'] + """ AS cat,
                            public.geometry_columns AS gc
                        WHERE
                            (
                                cat.""" + self.config['title_col'] + """ ILIKE %(search_text)s OR
                                cat.""" + self.config['abstract_col'] + """ ILIKE %(search_text)s
                            ) AND
                            cat.""" + self.config['schema_col'] + """ IS NOT NULL AND
                            cat.""" + self.config['table_col'] + """ IS NOT NULL AND
                            -- Join conditions:
                            cat.""" + self.config['schema_col'] + """ = gc.f_table_schema AND
                            cat.""" + self.config['table_col'] + """ = gc.f_table_name""", query_dict)

        # Clear the results
        self.search_results = []
        self.resultsListWidget.clear()

        for title, abstract, schema, table, geom_col, ty in cur.fetchall():
            res = dict()
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
                uri.setDataSource(res['schema'],
                                  res['table'],
                                  res['geom_col'])
                layer_name = '%s (%s)' % (res['title'], res['geom_type'].lower())
                vlayer = QgsVectorLayer(uri.uri(), layer_name, 'postgres')
                QgsMapLayerRegistry.instance().addMapLayer(vlayer)

    def display_details(self, current_row):
        """
            When a result is selected, display its details in the panel to the right.

        :param current_row: The index of the selection
        :return:
        """

        self.detailsPlainTextEdit.clear()
        if current_row < 0:
            return

        title = self.search_results[current_row]['title']
        # date = self.search_results[current_row]['date']
        abstract = self.search_results[current_row]['abstract']

        details_text = ''
        details_text += 'Title: %s\n\n' % title
        # details_text += 'Date: %s\n\n' % date

        details_text += 'Abstract: %s' % abstract

        self.detailsPlainTextEdit.appendPlainText(details_text)

    def on_result_sel_changed(self):
        # Determine if we have a selection, if so, enable the add features button
        if len(self.resultsListWidget.selectedItems()) > 0:
            self.addSelectedPushButton.setEnabled(True)
        else:
            self.addSelectedPushButton.setEnabled(False)