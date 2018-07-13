# Hubspot Engagement API

Pull data from the Engagement data and store in a relational database.

From their [documentation](https://developers.hubspot.com/docs/methods/engagements/engagements-overview):
_Engagements are used to store data from CRM actions, including notes, tasks, meetings, and calls. Engagements should be associated with at least one contact record, and optionally other contacts, deals, and a company record._

That leads to a nice entity relationship diagram:

![Entity Relationship Diagram](https://github.com/thef1rstpancake/hubspot/blob/master/misc/ERD.png)

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

Leveraging the `/engagements/v1/engagements/recent/modified` endpoint gives us all of the recent engagements within the last 30 days.  This gave us little under 100 records to work with, so not a lot of data, but enough to get a good query.

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

The `createdAt` field is in milliseconds.  We can convert it to a datetime by dividing the value by 1000 and then convert it to a datetime via `FROM_UNIXTIME`.  

