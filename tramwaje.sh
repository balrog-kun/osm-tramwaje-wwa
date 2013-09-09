date=20100118
for i in $date/*/*.HTM; do iconv --from-code=windows-1250 --to-code=utf8 < $i > x ; mv x $i ; done
./ztm-routes.py $date/? $date/??
xmllint --format routes.xml >o
mv o routes.xml 

wget "http://www.informationfreeway.org/api/0.6/node[bbox=20.7,51.1,21.2,52.5][railway=tram_stop]" -O stops.osm 
wget "http://www.informationfreeway.org/api/0.6/way[bbox=20.7,51.1,21.2,52.5][railway=tram]" -O ways.osm 
wget "http://www.informationfreeway.org/api/0.6/relation[bbox=20.7,51.1,21.2,52.5][route=tram]" -O routes.osm 
./osm-merge stops.osm ways.osm > stops-and-ways.osm
./osm-merge stops-and-ways.osm routes.osm > data.osm
rm stops.osm ways.osm routes.osm stops-and-ways.osm

./routemaker.py
./osm-merge data.osm routes.osm > newdata.osm
