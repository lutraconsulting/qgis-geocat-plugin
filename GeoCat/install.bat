@echo off

rem /***************************************************************************
rem  GeoCat
rem                                  A QGIS plugin
rem  Search for PostGIS tables using metadata.
rem                              -------------------
rem         begin                : 2015-11-24
rem         copyright            : (C) 2015 Peter Wells for Lutra Consulting
rem         email                : info@lutraconsulting.co.uk
rem         git sha              : $Format:%H$
rem  ***************************************************************************/
rem 
rem /***************************************************************************
rem  *                                                                         *
rem  *   This program is free software; you can redistribute it and/or modify  *
rem  *   it under the terms of the GNU General Public License as published by  *
rem  *   the Free Software Foundation; either version 2 of the License, or     *
rem  *   (at your option) any later version.                                   *
rem  *                                                                         *
rem  ***************************************************************************/

SET DEST=%HOMEPATH%\.qgis2\python\plugins\GeoCat
mkdir %DEST%
xcopy /e /y *.py %DEST%
xcopy /e /y *.png %DEST%
xcopy /e /y metadata.txt %DEST%
xcopy /e /y *.ui %DEST%
xcopy /e /y *.qrc %DEST%
PAUSE