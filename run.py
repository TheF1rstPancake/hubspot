import mysql.connector
import os
import requests
import datetime

def hub(endpoint, payload, method="get"):
    """
    make calls to hubspot
    """

    base = "https://api.hubapi.com"
    method = method.lower()      
    url = "{0}{1}".format(base, endpoint)
    data = {"hapikey": os.environ.get('HAPIKEY', "demo")}
    if method != "post":
      data = {**data, **payload}
      return requests.__getattribute__(method)(url,params=data)
    else:
      return requests.__getattribute__(method)(url, params=data, json=payload)

def initializeDatabase(cxr):
  """
  Initialize the database.  The database will be named `hubspot`.
  It will also initialize the engagements table

  .. note::
    We will drop the engagements table if it already exists

  :param cxr: A MySql.connector object connected to the MySql instance
  """
  # stealing a lot of this from https://dev.mysql.com/doc/connector-python/en/connector-python-example-ddl.html
  TABLES = {}
  TABLES['engagements'] = (
    "CREATE TABLE `engagements` ("
    "  `id` int NOT NULL,"
    "  `portalId` int,"
    "  `active` boolean,"
    "  `createdAt` bigint,"
    "  `lastUpdated` bigint,"
    "  `createdBy` bigint,"
    "  `modifiedBy` bigint,"
    "  `timestamp` bigint,"
    "  `ownerId` int,"
    "  `type` text,"
    "  `uid` text,"
    "  `source` text,"
    "  PRIMARY KEY (`id`)"
    ")")


  # create database
  cursor = cxr.cursor()
  
  try:
    cursor.execute(
      "CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8'".format("hubspot")
    )
  except mysql.connector.Error as err:
    if err.errno != 1007:
      print("Failed creating table: {}".format(err))
      exit(1)
    else: 
      print("Warning database 'hubspot' already exists.")
  cursor.close()

  # create tables
  for k, v in TABLES.items():
    print("Creating table: {0}".format(k))
    createTable(cxr, v, k)

def createTable(cxr, command, table):
  """
  Create a table

  :param cxr: A MySql.connector object connected to the MySql instance
  :param command: A string representing the command to create a table 
  :param table: the name of the table
  """
  cursor = cxr.cursor()
  try:
    cursor.execute("DROP TABLE IF EXISTS `{0}`".format(table))
  except mysql.connector.Error as err:
    print(err)
    exit(1)

  try:
    cursor.execute(command)
  except mysql.connector.Error as err:
    if err.errno != 1050:
      print("Failed creating table: {}".format(err))
      exit(1)
    else: 
      print("Warning table already exists.")
  cxr.commit()
  cursor.close()

def writeToTable(cxr, data, table):
  """
  Write a list of data elements into a given table

  :param cxr: A MySql.connector object connected to the MySql instance
  :param data: A list of dictionaries containing the data to write to the table
  :param table: Name of the table to write data to
  """
  # write each data element to the table
  # pull out the keys and list them out
  # and then pull out the values and list them out
  # this ensures that we are inserting the right values into the right columns
  cursor = cxr.cursor()
  print("Writing data")
  for d in data:
    # build the insertion string and specify what fields
    # we are writing into
    insertion_string = "INSERT INTO {0} ({1}) VALUES ({2})"
    names = ", ".join(["`{0}`".format(k) for k in d.keys()])
    values = ", ".join(["%s" for _ in d.keys()])

    # actually insert the data
    cursor.execute(insertion_string.format(table, names, values), list(d.values()))

  # commit data
  cxr.commit()
  return cursor.close()
if __name__ == "__main__":
  # assuming user is root and no password
  connector = mysql.connector.connect(host='localhost',database='mysql',user='root',password='')

  initializeDatabase(connector)

  # we could multi-thread this if we wanted to
  # but let's not
  # we are going to ask the API to give us all recent engagements
  # this only goes back 30 days, but that should be plenty
  hasMore = True
  i = 0
  while hasMore:
    r = hub("/engagements/v1/engagements/recent/modified", {"offset":i*100, "count":100})
    d = r.json()

    # format the data into a list of rows
    l = [e['engagement'] for e in d['results']]
    writeToTable(connector, l, "engagements")

    i = i+1
    hasMore = d['hasMore']

  # write a query to pull out the results 
  cursor = connector.cursor()
  cursor.execute("SELECT type, DATE(FROM_UNIXTIME(createdAt/1000)) as day, COUNT(*) as num_engagements FROM engagements GROUP BY type, day ORDER BY type, day ASC")

  # print each result out on a newline
  print("\n".join([str(x) for x in list(cursor)]))
  
  # close the connection
  cursor.close()
  connector.close()
  
  