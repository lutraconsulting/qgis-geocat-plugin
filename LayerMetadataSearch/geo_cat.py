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
import psycopg2

from qgis.PyQt.QtCore import Qt, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon

from qgis.core import QgsSettings

from .geo_cat_dialog import GeoCatDialog
from .geo_cat_config_dialog import GeoCatConfigDialog
from .gc_utils import resources_path
from .errors import CustomColumnException, ConnectionException
from .user_communication import UserCommunication


class GeoCat(object):
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.uc = UserCommunication(iface, 'Metadata Plugin')
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QgsSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'GeoCat_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = GeoCatDialog(iface)
        self.dlg.setWindowFlags(self.dlg.windowFlags() |
                       Qt.WindowSystemMenuHint |
                       Qt.WindowMinMaxButtonsHint)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Layer Metadata Search')
        self.toolbar = self.iface.addToolBar(u'Layer Metadata Search')
        self.toolbar.setObjectName(u'Layer Metadata Search')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Layer Metadata Search', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.add_action(
            resources_path('cat_dialog.png'),
            text=self.tr(u'Search For Tables Using Metadata'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.add_action(
            resources_path('cat_config.png'),
            text=self.tr(u'Configure Layer Metadata Search'),
            callback=self.configure,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.dlg.close()
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Layer Metadata Search'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.dlg, self.toolbar

    def is_configured(self):
        """Check if the plugin is configured."""
        s = QgsSettings()
        s.beginGroup('GeoCat')
        conn = s.value('connection', '', type=str)
        s.endGroup()
        return conn != ''

    def run(self):
        """Run method that performs all the real work"""
        if not self.is_configured():
            self.uc.show_warn('Please configure the plugin first!')
            self.configure()
        self.dlg._setup_config()
        # refresh custom columns widgets
        try:
            self.dlg.setup_custom_widgets()
        except (ConnectionException, psycopg2.OperationalError) as e:
            # Report back what we tried to connect with
            from .dbutils import get_postgres_conn_info_and_meta
            con_info, con_meta = get_postgres_conn_info_and_meta(self.dlg.config['connection'])
            self.uc.show_warn('Database connection error. '
                              f'Settings used to connect where: host="{str(con_info["host"])}" ({type(con_info["host"])}), '
                              f'port="{str(con_info["port"])}" ({type(con_info["port"])}), '
                              f'database="{str(con_info["database"])}" ({type(con_info["database"])}), '
                              f'user="{str(con_info["user"])}" ({type(con_info["user"])})\n\n{repr(e)}'
                              )
            return
        except CustomColumnException as e:
            self.uc.show_warn(e[0])
            return

        # clear any previuos search text and results
        self.dlg.browseAllCheckBox.setCheckState(Qt.Unchecked)
        self.dlg.searchLineEdit.clear()
        self.dlg.clear_results()
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def configure(self):
        """Run method that performs all the real work"""
        # show the dialog
        config_dlg = GeoCatConfigDialog(self.iface)
        # Run the dialog event loop
        config_dlg.exec_()
