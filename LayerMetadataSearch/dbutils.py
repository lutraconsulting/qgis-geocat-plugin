# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DB utils
                                 QGIS plugin utils
 Database utils for working with QGIS plugins
                              -------------------
        begin                : 2015-11-24
        git sha              : $Format:%H$
        copyright            : (C) 2015 Lutra Consulting
        email                : info@lutraconsulting.co.uk
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
import psycopg2
from qgis.PyQt.QtCore import QSettings, QVariant
from qgis.core import QgsAuthMethodConfig, QgsApplication


def get_connection(conn_info):
    """ Connect to the database using conn_info dict:
     { 'host': ..., 'port': ..., 'database': ..., 'username': ..., 'password': ... }
    """
    try:
        conn = psycopg2.connect(**conn_info)
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except psycopg2.OperationalError:
        return None


def get_postgres_connections():
    """ Read PostgreSQL connection names from QSettings stored by QGIS
    """
    settings = QSettings()
    settings.beginGroup(u"/PostgreSQL/connections/")
    return settings.childGroups()


"""
def current_postgres_connection():
    settings = QSettings()
    settings.beginGroup("/PostGISSearch")
    return settings.value("connection", "", type=str)
"""


def get_postgres_conn_info_and_meta(selected):
    # import pydevd; pydevd.settrace()
    """ Read PostgreSQL connection details from QSettings stored by QGIS
    """
    settings = QSettings()
    settings.beginGroup(u"/PostgreSQL/connections/" + selected)
    if not settings.contains("database"): # non-existent entry?
        return {}

    conn_info = {}
    conn_meta = {}
    conn_info["host"] = settings.value("host", "", type=str)
    conn_info["port"] = settings.value("port", 5432, type=int)
    conn_info["database"] = settings.value("database", "", type=str)
    username = settings.value("username", "", type=str)
    password = settings.value("password", "", type=str)
    authconf = settings.value('authcfg', None)
    estimated_metadata = settings.value('estimatedMetadata', 'false', type=str)
    conn_meta["estimated_metadata"] = estimated_metadata == 'true'
    if authconf:
        auth_manager = QgsApplication.authManager()
        conf = QgsAuthMethodConfig()
        auth_manager.loadAuthenticationConfig(authconf, conf, True)
        if conf.id():
            conn_info["user"] = conf.config('username', '')
            conn_info["password"] = conf.config('password', '')
    else:
        conn_info["user"] = username
        conn_info["password"] = password
    # Check for the replace QVariant(NULL) with None (else connection errors)
    if conn_info["user"] == QVariant() or conn_info["user"] == '':
        conn_info["user"] = None
    if conn_info["password"] == QVariant() or conn_info["password"] == '':
        conn_info["password"] = None
    return conn_info, conn_meta


def _quote(identifier):
    """ quote identifier """
    return u'"%s"' % identifier.replace('"', '""')


def _quote_str(txt):
    """ make the string safe - replace ' with '' """
    return txt.replace("'", "''")


def list_schemas(cursor):
    """ Get list of schema names
    """
    sql = "SELECT nspname FROM pg_namespace WHERE nspname !~ '^pg_' AND nspname != 'information_schema'"
    cursor.execute(sql)

    names = [row[0] for row in cursor.fetchall()]
    return sorted(names)


def list_tables(cursor, schema):
    sql = """SELECT pg_class.relname
                FROM pg_class
                JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
                WHERE pg_class.relkind IN ('v', 'r') AND nspname = '%s'
                ORDER BY nspname, relname""" % _quote_str(schema)
    cursor.execute(sql)
    names = [row[0] for row in cursor.fetchall()]
    return sorted(names)


def list_columns(cursor, schema, table):
    sql = """SELECT a.attname AS column_name
        FROM pg_class c
        JOIN pg_attribute a ON a.attrelid = c.oid
        JOIN pg_namespace nsp ON c.relnamespace = nsp.oid
        WHERE c.relname = '%s' AND nspname='%s' AND a.attnum > 0
        ORDER BY a.attnum""" % (_quote_str(table), _quote_str(schema))
    cursor.execute(sql)
    names = [row[0] for row in cursor.fetchall()]
    return sorted(names)


def get_first_column(cursor, schema, table):
    sql = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = '{}'
    AND table_name = '{}'
    LIMIT 1""".format(schema, table)
    cursor.execute(sql)
    first_column = cursor.fetchall()[0][0]
    return first_column


def get_search_sql(search_text, geom_column, search_column, display_columns, extra_expr_columns, schema, table):
    """ Returns a tuple: (SQL query text, dictionary with values to replace variables with).
    """

    """
    Spaces in queries
        A query with spaces is executed as follows:
            'my query'
            ILIKE '%my%query%'

    A note on spaces in postcodes
        Postcodes must be stored in the DB without spaces:
            'DL10 4DQ' becomes 'DL104DQ'
        This allows users to query with or without spaces
        As wildcards are inserted at spaces, it doesn't matter whether the query is:
            'dl10 4dq'; or
            'dl104dq'
    """

    wildcarded_search_string = ''
    for part in search_text.split():
        wildcarded_search_string += '%' + part
    wildcarded_search_string += '%'
    query_dict = {'search_text': wildcarded_search_string}

    query_text = """ SELECT
                        ST_AsText("%s") AS geom,
                        ST_SRID(geom) AS epsg,
                 """ % geom_column
    query_text += """"%s"
                  """ % search_column
    if len(display_columns) > 0:
        for display_column in display_columns.split(','):
            query_text += """ || CASE WHEN "%s" IS NOT NULL THEN
                                    ', ' || "%s"
                                ELSE
                                    ''
                                END
                          """ % (display_column, display_column)
    query_text += """ AS suggestion_string """
    for extra_column in extra_expr_columns:
        query_text += ', "%s"' % extra_column
    query_text += """
                  FROM
                        "%s"."%s"
                     WHERE
                        "%s" ILIKE
                  """ % (schema, table, search_column)
    query_text += """   %(search_text)s
                  """
    query_text += """ORDER BY
                        "%s"
                    LIMIT 20
                  """ % search_column

    return query_text, query_dict
