# cloud-dining-concierge

Team Members:
---------------------
Shohna Kanchan - sk11239
Devyani Bairagya - db4922

cli commands for es
Index creation:
--------------
curl -u master_username:master_password -X PUT "https://search-dining-es-ogz7pvompabqcedjjmdpaxizsi.us-east-1.es.amazonaws.com/restaurants?pretty"

Bulk Loading of Data:
---------------------

curl -s "s3://sk11239-es/restaurant_data.json" >> output.json

curl -XPUT -u 'master_username:master_password' 'https://search-dining-es-ogz7pvompabqcedjjmdpaxizsi.us-east-1.es.amazonaws.com/restaurants/_bulk?pretty' --data-binary @/output.json -H 'Content-Type: application/json'

Kibana search query:
---------------------

GET restaurants/_search
{
  "query": {
    "match_all": { }
  },
  "size": 200
}
