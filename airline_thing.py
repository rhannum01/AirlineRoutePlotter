#!/usr/bin/env python3
import argparse, re

import pandas as pd
import plotly.offline as py
import plotly.graph_objs as go

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--airports", help="airports.csv to use", required=True)
    parser.add_argument("-r", "--routes", help="routes.csv to use", required=True)
    parser.add_argument("-e", "--equipment", help="plane type", required=False)

    args = parser.parse_args()

    data = AirlineData(args.airports, args.routes)
    equipment_list = data.get_equipment_list()
    if args.equipment not in equipment_list:
        print("Pick one of the following planes: {}".format(re.sub("['']", "",str(equipment_list))))
        args.equipment = equipment_list
    data.show_map(args.equipment)

class AirlineData:
    def __init__(self, airports_file, routes_file):
        self.raw_airports = pd.read_csv(airports_file)
        self.raw_routes = pd.read_csv(routes_file)
        self._parse_data()
        self._draw_base_map()

        #self.map.to_html('./prototype.html')
    def show_map(self, equipment):
        self._populate_airport_trace()
        self._populate_route_traces(equipment)
        self.map.show()
    def get_equipment_list(self):
        equipment = self.raw_routes.groupby(['Equipment']).size().reset_index()
        equipment = equipment['Equipment'].to_list()
        return equipment

    def _draw_base_map(self):
        self.map = go.Figure(go.Scattergeo())
        self.map.update_layout(go.Layout(
            showlegend = False,
            autosize=True,
            paper_bgcolor = 'rgb(29, 29, 29)',
            plot_bgcolor = 'rgb(29, 29, 29)'
        ))
        self.map.update_geos(
            scope='world',
            projection=dict( type='equal earth' , scale = 1),
            #projection=dict( type='orthographic' , scale = 1),
            showland = True,
            showocean = True,
            showlakes = False,
            showcoastlines = True,
            showcountries = True,
            landcolor = 'rgb(49, 49, 49)',
            countrycolor = 'rgb(90, 90, 90)',
            coastlinecolor = 'rgb(90, 90, 90)',
            oceancolor = 'rgb(29, 29, 29)',
            bgcolor = 'rgb(29, 29, 29)',
        )

    def _parse_data(self):

        # count number of trips taken with unique src, dest, and equipment
        self.routes = self.raw_routes.groupby(['Source airport', 'Destination airport', 'Equipment']).size().reset_index(name='count')

        # get lat/long for each src airport
        self.routes = pd.merge(self.routes, self.raw_airports[['IATA','Latitude','Longitude']],
              how='inner', left_on='Source airport', right_on='IATA', suffixes=('_Orig','_Dest'))

        # get lat/long for each dest airport
        self.routes = pd.merge(self.routes, self.raw_airports[['IATA','Latitude','Longitude']],
                    how='inner', left_on='Destination airport', right_on='IATA', suffixes=('_Orig','_Dest'))


        print(self.routes)
        self.airports = self.raw_airports
        # count number of times each airport was the src
        source_count = self.raw_routes.groupby(['Source airport']).size().reset_index(name='source count')
        source_count.rename(columns={'Source airport': 'IATA'}, inplace=True)
        # count number of times each airport was the dest
        dest_count =  self.raw_routes.groupby(['Destination airport']).size().reset_index(name='dest count')
        dest_count.rename(columns={'Destination airport': 'IATA'}, inplace=True)


        self.airports = pd.merge(self.airports, source_count, left_on='IATA', right_on='IATA', how='outer')
        self.airports = pd.merge(self.airports, dest_count, left_on='IATA', right_on='IATA', how='outer')
        self.airports.fillna(0, inplace=True)
        self.airports['total count'] = self.airports['source count'] + self.airports['dest count']

        print (self.airports)

    def _populate_airport_trace(self):
        self.map.add_trace(go.Scattergeo(
            type = 'scattergeo',
            locationmode = 'ISO-3',
            showlegend = False,
            lon = self.airports['Longitude'],
            lat = self.airports['Latitude'],
            hoverinfo = 'text',
            text = self.airports['IATA'] + 'count: '+ self.airports['total count'].map(str),
            mode = 'markers',
            marker = dict(
                sizemin=2,
                size=(self.airports['total count']/max(self.airports['total count']))*35,
                color='rgb(0, 150, 255)',
            )
        ))

    def _populate_route_traces(self, equipment):
        for i in range(len(self.routes)):
            if self.routes['Equipment'][i] not in equipment:
                continue
            self.map.add_trace(go.Scattergeo(
                type = 'scattergeo',
                locationmode = 'ISO-3',
                showlegend = False,
                hoverinfo='text',
                text = "{} <-> {}: {}".format(self.routes['Source airport'][i], self.routes['Destination airport'][i], self.routes['count'][i]),
                lon = [self.routes['Longitude_Orig'][i], self.routes['Longitude_Dest'][i]],
                lat = [self.routes['Latitude_Orig'][i], self.routes['Latitude_Dest'][i]],
                mode = 'lines',
                line = dict(
                    width=max((self.routes['count'][i]/max(self.routes['count']))*5, 0.25),
                    color='rgb(255,215,0)',
                )
            ))



if __name__ == "__main__":
    main()