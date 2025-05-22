#!/opt/franchisfeed/venv/bin/python

import os
import psycopg2
import pandas as pd
import paramiko
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env-Datei
load_dotenv("/opt/franchisfeed/.env")

# Redshift-Verbindungsdaten
DB_PARAMS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

# SFTP-Verbindungsdaten
SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_PORT = int(os.getenv("SFTP_PORT"))
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")
SFTP_REMOTE_DIR = os.getenv("SFTP_REMOTE_DIR")

# Export-Dateiname
EXPORT_FILENAME = "franchisefeed.csv"

# SQL-Query
SQL_QUERY = """
with item_name_prep AS (
  SELECT
  di.item_code,
  di.item_name,
  di.item_gtin,
  MAX(CASE WHEN m.spras = 'E' THEN m.maktx END) AS en_maktx,
  MAX(CASE WHEN m.spras = 'D' THEN m.maktx END) AS de_maktx,
  MAX(CASE WHEN m.spras = 'K' THEN m.maktx END) AS k_maktx,
  mtp.name_de
  FROM star_analytical.d_item di
  LEFT JOIN  sap_erp_replication_spectrum.makt m ON di.item_code = m.matnr
  LEFT JOIN (
      SELECT 
      id as item_code,
      name_de 
      FROM module_tool.products
      WHERE meta_date = (SELECT max(meta_date) FROM module_tool.products)
      QUALIFY ROW_NUMBER() OVER (PARTITION BY id, name_de) = 1
  ) AS mtp
  ON mtp.item_code = di.item_code
  WHERE 
    di.item_purchaser_group='B01'
  GROUP BY di.item_code, di.item_name, di.item_gtin, mtp.name_de
)
,cte1 as (
  select 
    item_code
    ,item_parent_name
    ,item_name
    ,item_colors
  	,item_series
    ,item_materials
    ,item_attributes_height
    ,item_attributes_width
    ,item_attributes_depth
    ,item_gross_weight
    ,item_net_weight
    ,item_first_sellable_date  	
  	,item_purchaser_group
  from star_analytical.d_item 
  where   	
  	item_purchaser_group='B01'
  	--and	item_code='000000001000341553' 
)
, cte2 as (
  select 
     item_catalog.item_code
    ,item_catalog.item_name
    ,item_catalog.item_cleaned_name
    ,item_catalog.item_attributes_legacy_sku
    ,item_catalog.item_attributes_ean
    ,item_catalog.item_attributes_material_detail
    ,item_catalog.item_attributes_color_detail
    ,item_catalog.item_attributes_color
    ,item_catalog.item_attributes_color_sub_color
    ,item_catalog.item_attributes_height
    ,item_catalog.item_attributes_width
    ,item_catalog.item_attributes_depth
    ,item_catalog.item_attributes_material
    ,item_catalog.item_stock_quantity
    ,item_catalog.item_offer_shipping_delivery_time
  	,item_catalog.item_first_image_link
  from public.item_catalog
  join cte1 on cte1.item_code=item_catalog.item_code
  where 
  	app_domain_id=1
 )
 ,cte_eans as (
    select distinct 
   		p.id as item_code, p.ean
    from module_tool.products p
    where
      p.meta_date = (select max(meta_date) from module_tool.products)      
 ),cte_en_name as (
     select 
       item_catalog.item_code
   		,item_catalog.item_name
      ,item_catalog.item_name_alternative
      ,item_catalog.item_cleaned_name
   		,'en_US'::varchar as item_language
    from public.item_catalog
    join star_analytical.d_item on 
      d_item.item_code=item_catalog.item_code 
      and d_item.item_purchaser_group='B01'
    where
      item_catalog.app_domain_id=21
      and item_catalog.item_language='en_US'
  )
 

 select 
 	 cte1.item_code
	,coalesce(nullif(TRIM(item_name_prep.en_maktx),''), item_name_prep.de_maktx) as description  
  --,case when TRIM(item_name_prep.en_maktx)!='' then 'en_US'::varchar else 'de_DE'::varchar end as item_language
	,case when cte1.item_series='UNKNOWN' then '' else cte1.item_series end as item_series
  ,isnull(cte2.item_attributes_legacy_sku,'') as item_attributes_legacy_sku
  ,case when cte2.item_attributes_ean='UNKNOWN' then '' else cte2.item_attributes_ean end as item_attributes_ean
  ,REPLACE(SUBSTRING(REPLACE(cte_eans.ean,cte2.item_attributes_ean,''),2,500),'||','|') as additional_eans
	,case when cte1.item_attributes_height::VARCHAR='UNKNOWN' then '' else cte1.item_attributes_height::VARCHAR end as item_attributes_height
	,case when cte1.item_attributes_width::VARCHAR='UNKNOWN' then '' else cte1.item_attributes_width::VARCHAR end as item_attributes_width
	,case when cte1.item_attributes_depth::VARCHAR='UNKNOWN' then '' else cte1.item_attributes_depth::VARCHAR end as item_attributes_depth
	,case when cte1.item_gross_weight::VARCHAR='UNKNOWN' then '' else cte1.item_gross_weight::VARCHAR end as item_gross_weight
	,case when cte1.item_net_weight::VARCHAR='UNKNOWN' then '' else cte1.item_net_weight::VARCHAR end as item_net_weight
  ,case when cte1.item_colors='UNKNOWN' then '' else cte1.item_colors end as item_colors
  ,case when cte1.item_materials='UNKNOWN' then '' else cte1.item_materials end as item_materials
  ,isnull(case when cte2.item_stock_quantity::VARCHAR='UNKNOWN' then '' else cte2.item_stock_quantity::VARCHAR end,'0') as item_stock_quantity
  ,isnull(case when cte2.item_offer_shipping_delivery_time::VARCHAR='UNKNOWN' then '' else cte2.item_offer_shipping_delivery_time::VARCHAR end,'0') as item_offer_shipping_delivery_time
  ,isnull(case when cte2.item_first_image_link='UNKNOWN' then '' else cte2.item_first_image_link end,'') as item_first_image_link
 from cte1 
 left join cte2 on cte2.item_code=cte1.item_code
 left join cte_eans on cte_eans.item_code=cte1.item_code
 left join item_name_prep on item_name_prep.item_code=cte1.item_code
"""

def export_to_csv():
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        df = pd.read_sql_query(SQL_QUERY, conn)
        df.to_csv(EXPORT_FILENAME, index=False, sep=';', quoting=1, quotechar='"')
        print("✅ CSV erfolgreich erstellt.")
    except Exception as e:
        print(f"❌ Fehler beim Export: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def upload_to_sftp():
    try:
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        remote_path = os.path.join(SFTP_REMOTE_DIR, EXPORT_FILENAME)
        sftp.put(EXPORT_FILENAME, remote_path)
        print(f"✅ Datei erfolgreich hochgeladen: {remote_path}")
        sftp.close()
        transport.close()
    except Exception as e:
        print(f"❌ Fehler beim SFTP-Upload: {e}")

if __name__ == "__main__":
    export_to_csv()
    upload_to_sftp()