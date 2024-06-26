# Databricks notebook source
# DBTITLE 1,Creation of Widgets
dbutils.widgets.text("LoadType", "Full")
v_loadType = dbutils.widgets.get("LoadType")
dbutils.widgets.text("SchemaName", "SalesLT")
v_schemaName = dbutils.widgets.get("SchemaName")


# COMMAND ----------

# DBTITLE 1,Validation of Widgets
v_schemaName+' '+v_loadType

from datetime import date
today = date.today()
print(date.today().strftime("%Y")+"/"+date.today().strftime("%m")+"/"+date.today().strftime("%d")+"/")


# COMMAND ----------

# DBTITLE 1,Execute necessary functions
# MAGIC %run 
# MAGIC "./FunctionsNotebook"

# COMMAND ----------

# DBTITLE 1,Importing Required Functions
from pyspark.sql.functions import col,lit,to_date

# COMMAND ----------

# DBTITLE 1,GetTable Name from the Bronze Container
bronzeSchemaPath= bronzePath+v_schemaName+'/'
silverSchemaPath= silverPath+v_schemaName+'/'
bronzeTables = getTables(bronzeSchemaPath)
print(bronzeTables)
#print(silverPath)

# COMMAND ----------

# DBTITLE 1,Performing Transformations and Writting into Silver in Delta format
watermarkdf = spark.read.jdbc(Connection_String, "audit.WaterMark").cache()
for i in bronzeTables:
    bronzeTablePath = bronzeSchemaPath+i+"/"+date.today().strftime("%Y")+"/"+date.today().strftime("%m")+"/"+date.today().strftime("%d")+"/"+i+".parquet"
    print(i)
    silverPath = silverSchemaPath+i+"/"
    df = spark.read.format("parquet").option("mode","PERMISSIVE").load(bronzeTablePath)
    if v_schemaName=='SalesLT' and v_loadType.upper() != 'FULL':
        maxModifiedDate= findingWaterMark(watermarkdf,i)
        df_filtered =df.filter(col("ModifiedDate")>=maxModifiedDate)
    else:
        df_filtered=df
    df_removedRowGUIDModifiedDate = removingRowGUIDModifiedDate(df_filtered)
    df_withOutNulls =nullHandling(df_removedRowGUIDModifiedDate)
    df_addedAuditColumns=addAuditColumns(df_withOutNulls)
    df_Final= modifiyingTimestamp2Date(df_addedAuditColumns)
    #df_Final.display()
    if v_loadType.upper() == 'FULL' :
        df_Final.write.format("delta").mode("OVERWRITE").option("mergeSchema", "true").save(silverPath)
    else:
        for tableName,primaryKeys in primary_keys_dict.items() :
            if tableName == i:
                mergeDeltaData(df_Final, "silver_saleslt", tableName, primaryKeys)
                print(tableName+ " is merged")
    if v_schemaName=='SalesLT':
        profileStats(df_Final,i,"silver_saleslt")
    print(i+ " table is load")
if v_schemaName=='SalesLT':
    updationOfWaterMark(bronzeTables)
