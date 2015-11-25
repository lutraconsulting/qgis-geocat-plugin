# GeoCat

FIXME: Short intro to the plugin


![](./Images/geo_cat.png)

Geo Cat requires a PostgreSQL table with the following minmum information. Table column names need not be the same as those described below and can be configured as described below. 

**title** - Human readable title of the PostGIS layer, e.g. Ordnance Survey Open Roads.  
**abstract** - A nationally consistent, high-level and shareable view of GB's road network. OS Open Roads is a connected road network for Great Britain. It contains all classified roads (such as motorways and A & B roads) as well as officially named unclassified roads.
**schema** - The PostgreSQL schema containing the PostGIS table.
**table** - The name of the PostGIS table.

## Metadata Preparation

This section describes how to set up the metadata PostgreSQL table.

Create a new metadata table and schema if required:

	CREATE SCHEMA geocat;
	CREATE TABLE geocat.metadata
	(
		id serial NOT NULL,
		name text,
		abstract text,
		schema text,
		"table" text,
		CONSTRAINT metadata_pkey PRIMARY KEY (id)
	)
	WITH (
		OIDS=FALSE
	);

With the table created we can automatically populate it with layers we already have in our database. The following command will add rows to the metadata table for any tables with do not already have entries: 

	INSERT INTO geocat.metadata
		(schema, "table")
	SELECT
		f_table_schema,
		f_table_name
	FROM
		geometry_columns LEFT OUTER JOIN geocat.metadata ON 
			f_table_schema = "schema" AND 
			f_table_name = "table"
	WHERE
		"schema" IS NULL AND
		"table" IS NULL;
		
Now we can simply open the metadata table in pgAdminIII and add the titles and abstracts. 