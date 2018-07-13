# Hubspot Engagement API

Pull data from the Engagement data and store in a relational database.

## Details
This project requires the [mysql-connector](https://pypi.org/project/mysql-connector/) and [requests](http://docs.python-requests.org/en/master/) libraries.  It was developed using Python 3.5.  

There is one Python script in this repository that will run the entire operation.  That script will attempt to connect to a MySQL 5.6+ instance and create a "hubspot" database.  Within that database, it will create a single table called "engagements."

For connecting to the Hubspot API, we used their test api key value "demo."  If you want to use a different API key, you should set an environment variable "HAPIKEY" to whatever your key is.

To run the project:
```
python run.py
```

## Workflow
From their [documentation](https://developers.hubspot.com/docs/methods/engagements/engagements-overview):
_Engagements are used to store data from CRM actions, including notes, tasks, meetings, and calls. Engagements should be associated with at least one contact record, and optionally other contacts, deals, and a company record._

That leads to a nice entity relationship diagram:

![Entity Relationship Diagram](https://raw.githubusercontent.com/thef1rstpancake/hubspot/master/misc/ERD.png)

The different types of engagements aren't totally important for this project.  Ideally we would build out a table for each type of engagement with a foreign key pointing back to the engagement.  For this, we just need to be able to count the number of engagements a day and the number of engagments by type on a rolling 2 week average.

So we can hit the engagement API and pull several pages of data to load into our database.  The Hubspot API returns a "createTime" which is a Unix timestamp.  If we want to look at the number of engagements a day, we could convert that "createTime" to a date string at the time we pull it from the Hubspot API and store it directly in the database.  Or we can leverage MySQL's DATE function.

The HubSpot documentation lists only a few of the fields that actually come back from the API response.  We found several instances where we were receiving unexpected data such as a `source` column.  With a little trial and error, we finally got the full schema and created a table using the following command:

```python
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
    ")"
```

Leveraging the `/engagements/v1/engagements/recent/modified` endpoint returns all of the recent engagements within the last 30 days.  This provides little under 100 records to work with, so not a lot of data, but enough to get a good query.

We can then count all engagements, broken down by type, and day:

```sql
SELECT 
  type, 
  DATE(FROM_UNIXTIME(createdAt/1000)) as day, 
  COUNT(*) as num_engagements 
FROM engagements 
GROUP BY type, day
ORDER BY type, day ASC
```

The `createdAt` field is in milliseconds.  We can convert it to a datetime by dividing the value by 1000 and then convert it to a datetime via `FROM_UNIXTIME`.  Grouping by `type` and `day` then gives us a count of each type of engagement by day.  If an engagement did not happen on a given day, then it will not appear in the results.

```python
('CALL', datetime.date(2018, 7, 10), 1)
('EMAIL', datetime.date(2018, 6, 28), 1)
('EMAIL', datetime.date(2018, 6, 30), 1)
('INCOMING_EMAIL', datetime.date(2018, 6, 28), 1)
('INCOMING_EMAIL', datetime.date(2018, 7, 1), 1)
('NOTE', datetime.date(2018, 7, 2), 1)
('NOTE', datetime.date(2018, 7, 9), 2)
('NOTE', datetime.date(2018, 7, 10), 2)
('NOTE', datetime.date(2018, 7, 11), 8)
('NOTE', datetime.date(2018, 7, 12), 11)
('PUBLISHING_TASK', datetime.date(2018, 6, 25), 1)
('PUBLISHING_TASK', datetime.date(2018, 6, 28), 2)
('TASK', datetime.date(2018, 6, 15), 1)
('TASK', datetime.date(2018, 6, 17), 1)
('TASK', datetime.date(2018, 6, 18), 6)
('TASK', datetime.date(2018, 6, 19), 1)
('TASK', datetime.date(2018, 6, 21), 2)
('TASK', datetime.date(2018, 6, 25), 2)
('TASK', datetime.date(2018, 6, 26), 1)
('TASK', datetime.date(2018, 6, 28), 1)
('TASK', datetime.date(2018, 6, 29), 2)
('TASK', datetime.date(2018, 7, 1), 10)
('TASK', datetime.date(2018, 7, 10), 1)
('TASK', datetime.date(2018, 7, 13), 4)
```