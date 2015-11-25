# GeoCat

GeoCAT is short name for Geographic Information Systems Catalogue and is a plugin used to search GIS metadata. GeoCAT can be used to search data describing the "who, what, where, when and how" of map layers. GeoCAT was developed on behalf of Dartmoor National Park, UK.

FIXME: Update the image below.
![](./Images/geo_cat.png)

GeoCat requires metadata to be stored in a PostgreSQL table with the following minimum information. Table column names need not be exactly the same as those described below. 

**title** - Human readable title of the PostGIS layer, e.g. Ordnance Survey Open Roads.  

**abstract** - An abstract for the PostGIS layer, e.g. A nationally consistent, high-level and shareable view of GB's road network. OS Open Roads is a connected road network for Great Britain. It contains all classified roads (such as motorways and A & B roads) as well as officially named unclassified roads.

**schema** - The PostgreSQL schema containing the PostGIS table.

**table** - The name of the PostGIS table.

Once configured, GeoCat will search for PostGIS tables using both the title and abstract metadata fields.

## Configuration

GeoCat can be configured in QGIS via `Plugins` > `GeoCat` > `Configure GeoCat` which will open the following dialog:

![](./Images/geo_cat_config.png)

## Metadata Preparation

This section describes how to set up a PostgreSQL table for the matadata.

First, create a new metadata table and schema if required:

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

With the table created we can automatically populate it with layers we already have in our database. The following command will add rows to the metadata table for any tables not already featured in the metadata table: 

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
		
Now we can simply open the metadata table in pgAdminIII and add the titles and abstracts:

![](./Images/pgadmin.png)