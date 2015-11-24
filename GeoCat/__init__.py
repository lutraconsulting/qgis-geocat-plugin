# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeoCat
                                 A QGIS plugin
 Search for PostGIS tables using metadata
                             -------------------
        begin                : 2015-11-24
        copyright            : (C) 2015 Dartmoor National Park Authority
        email                : gi@dartmoor.gov.uk
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load GeoCat class from file GeoCat.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .geo_cat import GeoCat
    return GeoCat(iface)
