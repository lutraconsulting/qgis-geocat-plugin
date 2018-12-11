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
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtGui import QIcon


def load_ui(name):
    ui_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ui', name + '.ui')
    return uic.loadUiType(ui_file)[0]


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
    except TypeError:
        return False


def resources_path(*args):
    """Get the path to our resources folder.
    """
    path = os.path.dirname(__file__)
    path = os.path.abspath(
        os.path.join(path, 'resources'))
    for item in args:
        path = os.path.abspath(os.path.join(path, item))
    return path


def set_icon(btn, icon_file):
    ipath = resources_path('img', icon_file)
    # print ipath
    btn.setIcon(QIcon(ipath))


def resource_url(path):
    """Get the a local filesystem url to a given resource.
    """
    url = QtCore.QUrl.fromLocalFile(path)
    return str(url.toString())


