# Layer Metadata Search

Layer Metadata Search is a plugin used to search GIS metadata. Layer Metadata Search can be used to search data describing the "who, what, where, when and how" of map layers. Layer Metadata Search was developed on behalf of Dartmoor and Exmoor National Parks, UK.

![](./Images/geo_cat.png)

Layer Metadata Search requires metadata to be stored in a PostgreSQL table with the following minimum information. Table column names need not be exactly the same as those described below.

**title** - Human readable title of the dataset, e.g. *Ordnance Survey Open Roads* or *Aerial photos*.

**type** - Dataset type: *vector* or *raster*.

**abstract** - An abstract for the dataset, e.g. *A nationally consistent, high-level and shareable view of GB's road network. OS Open Roads is a connected road network for Great Britain. It contains all classified roads (such as motorways and A & B roads) as well as officially named unclassified roads.*

**other fields** - The plugin can also search on and display other custom metadata fields - described later.

**schema** - For vector datasets, the PostgreSQL schema containing the PostGIS table.

**table** - For vector datasets, the name of the PostGIS table.

**path** - For raster datasets, the path to the raster dataset.

Once configured, Layer Metadata Search will search for datasets using the title, abstract and any other custom metadata fields.


## Configuration

Layer Metadata Search can be configured in QGIS via `Plugins` > `Layer Metadata Search` > `Configure Layer Metadata Search` which will open the following dialog:

![](./Images/geo_cat_config.png)

The *Custom / additional metadata columns* section of the configuration is described later. 


## Metadata Preparation

This section describes how to set up a PostgreSQL table for the matadata.

First, create a new metadata table and schema if required:

	CREATE SCHEMA layer_metadata_search;
	CREATE TABLE layer_metadata_search.metadata
    (
      id serial NOT NULL,
      name text,
      type text NOT NULL DEFAULT 'vector'::text,
      abstract text,
      schema text, -- required for vector datasets
      "table" text, -- required for vector datasets
      path text, -- required for raster datasets
      keywords text, -- optional, one of the custom columns
      mod_date date, -- optional
      tstamp timestamp without time zone, -- optional
      -- insert other custom columns here as required
      CONSTRAINT metadata_pkey PRIMARY KEY (id)
    );

### Adding vector layers

With the table created we can automatically populate it with layers we already have in our database. The following query will add rows to the metadata table for any tables not already featured in the metadata table:

	INSERT INTO layer_metadata_search.metadata
		(schema, "table")
	SELECT
		f_table_schema,
		f_table_name
	FROM
		geometry_columns LEFT OUTER JOIN layer_metadata_search.metadata ON
			f_table_schema = "schema" AND 
			f_table_name = "table"
	WHERE
		"schema" IS NULL AND
		"table" IS NULL;

Now we can simply open the metadata table in pgAdminIII and add the titles and abstracts:

![](./Images/pgadmin.png)

### Adding raster layers

A raster dataset / layer may consist of a single image, or multiple image tiles which, together, make up the entire layer.

For tiled layers, users are encouraged to create virtual raster files (VRT) which reference all tiles within a layer in a single VRT file. This allows a single metadata entry to be added to the table describing the whole layer.

Virtual raster files can be easily created using [gdalbuildvrt](http://www.gdal.org/gdalbuildvrt.html) (part of GDAL). This tool can also be found in QGIS under *Raster* > *Miscellaneous* > *Build Virtual Raster*. 

For layers consisting of a single image there is no need to create a VRT file.

For raster files, the following columns of the metadata table should be populated as a minimum:

 * name (user-friendly name)
 * type (set to *raster*)
 * path (absolute path to the raster file)


## Using Custom Metadata Fields

This section describes how to make use of custom metadata fields in the Layer Metadata Search plugin.

1. First ensure that the metadata table contains the fields you wish to work with.
1. Now open up the configuration dialog:

	![](./Images/geo_cat_config_custom.png)

	The `+`/`-` buttons can be used to add new metadata entries.

	**Description** - how this field will be displayed in search results.

	**Column** - source metadata column.

	**Widget type** - How the metadata should be displayed.  Options include LineEdit (display as text across a single line), TextEdit (similar but across multiple lines) and DateEdit (for displaying dates).

	*Please note that when using the DateEdit widget the source column in the database should be of type `date`*


## Upgrading from previous versions

If you have an existing metadata table which was created before raster support was added to this plugin, you will need to modify the metadata table in the following manner:

    -- Add a column for layer type (vector/raster)
    ALTER TABLE layer_metadata_search.metadata ADD COLUMN type text NOT NULL default 'vector';

    -- Add a column for raster file path
    ALTER TABLE layer_metadata_search.metadata ADD COLUMN path text;

    -- Set the type for any existing vector layers
    UPDATE layer_metadata_search.metadata SET type = 'vector';

When adding a dataset, always specify its type as either *vector* or *raster*.