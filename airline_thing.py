#!/usr/bin/env python3
import argparse, re

import pandas as pd
import numpy as np
import plotly.offline as py
import plotly.graph_objs as go
from matplotlib import colors as mcolors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--airports_file", help="airports.csv to use", required=True)
    parser.add_argument("--routes_file", help="routes.csv to use", required=True)
    parser.add_argument("-e", "--equipment", nargs='+',help="planes to generate data for", required=False)
    parser.add_argument("-a", "--airports", nargs='+', help="airports to generate data for", required=False)
    parser.add_argument("-r", "--roles", help="role to generate data for (Captain, First Officer)", required=False)
    parser.add_argument("-c", "--color", help="uniform color to use for routes", required=False)

    args = parser.parse_args()

    data = AirlineData(args.airports_file, args.routes_file)
    equipment_list = data.get_equipment_list()
    if not args.equipment:
        args.equipment = equipment_list
    else:
        for plane in args.equipment:
            if plane not in equipment_list:
                print("Pick one of the following planes: {}".format(re.sub("['']", "",str(equipment_list))))
                args.equipment = equipment_list

    if not args.roles:
        args.roles = ['CA','RC','FO','FB','FC']
    elif str(args.roles) == 'Captain':
        args.roles = ['CA','RC']
    elif str(args.roles) == 'First Officer':
        args.roles = ['FO','FB','FC']
    print(args.color)
    data.show_map(args.equipment, args.color, args.airports, args.roles)

class AirlineData:
    def __init__(self, airports_file, routes_file, airport_list=None):
        self.airports_raw = pd.read_csv(airports_file)
        self.routes_raw = pd.read_csv(routes_file)

        self.routes_filtered= pd.DataFrame()
        self.airports_filtered= pd.DataFrame()

        self.routes = pd.DataFrame()
        self.airports = pd.DataFrame()

        self._import_data()
        self._draw_base_map()

        #self.map.to_html('./prototype.html')
    def show_map(self, equipment, color, airport_list, roles):
        self._filter_routes_by_airport(airport_list)
        self._filter_routes_by_plane(equipment)
        self._filter_routes_by_role(roles)

        self._count_airport_visits()
        self._count_route_frequency()

        print(self.airports)
        print(self.routes)

        #self._update_map_center(airport_list)
        self._populate_route_traces(equipment, color)
        self._populate_airport_trace()

        self.map.show()
    def get_equipment_list(self):
        blacklist = ['300', '319', '320', '321']
        equipment = self.routes_raw.groupby(['Equipment']).size().reset_index()
        equipment = equipment['Equipment'].to_list()

        for plane in blacklist:
            if plane in equipment:
                equipment.remove(plane)
        return equipment

    def _import_data(self):
        # get lat/long for each src airport
        self.routes_raw = pd.merge(self.routes_raw, self.airports_raw[['IATA','Latitude','Longitude']],
              how='inner', left_on='Source airport', right_on='IATA', suffixes=('_Orig','_Dest'))

        # get lat/long for each dest airport
        self.routes_raw = pd.merge(self.routes_raw, self.airports_raw[['IATA','Latitude','Longitude']],
                    how='inner', left_on='Destination airport', right_on='IATA', suffixes=('_Orig','_Dest'))
        self.routes_filtered = self.routes_raw
        self.airports_filtered = self.airports_raw

    def _filter_routes_by_airport(self, airport_list):
        if not airport_list:
            return
        routes = pd.DataFrame()
        for airport in airport_list:
            routes = pd.concat([routes, self.routes_filtered[self.routes_filtered['IATA_Orig'].isin([airport]) |
                                                    self.routes_filtered['IATA_Dest'].isin([airport])]])
        self.routes_filtered = routes.reset_index(drop=True)

    def _filter_routes_by_plane(self, equipment_list):
        if not equipment_list:
            return
        routes = pd.DataFrame()
        for plane in equipment_list:
            routes = pd.concat([routes, (self.routes_filtered[self.routes_filtered['Equipment'].isin([plane])])])
        self.routes_filtered = routes.reset_index(drop=True)

    def _filter_routes_by_role(self, roles):
        if not roles:
            return
        routes = pd.DataFrame()
        for role in roles:
            print(role)
            routes = pd.concat([routes, (self.routes_filtered[self.routes_filtered['Role'].isin([role])])])
        self.routes_filtered = routes.reset_index(drop=True)

    def _count_airport_visits(self):
        # count number of times each airport was the src
        source_count = self.routes_filtered.groupby(['Source airport']).size().reset_index(name='source count')
        source_count.rename(columns={'Source airport': 'IATA'}, inplace=True)
        # count number of times each airport was the dest
        dest_count =  self.routes_filtered.groupby(['Destination airport']).size().reset_index(name='dest count')
        dest_count.rename(columns={'Destination airport': 'IATA'}, inplace=True)
        # append the counts to the airport list
        self.airports = self.airports_filtered
        self.airports = pd.merge(self.airports, source_count, left_on='IATA', right_on='IATA', how='outer')
        self.airports = pd.merge(self.airports, dest_count, left_on='IATA', right_on='IATA', how='outer')
        self.airports.fillna(0, inplace=True)
        # compute total counts
        self.airports['total count'] = self.airports['source count'] + self.airports['dest count']
        self.airports.sort_values(by=['total count'], inplace=True, ascending=False)
        self.airports = self.airports.loc[self.airports['total count'] > 0.1]
        print(self.airports)

    def _count_route_frequency(self):
        # count number of trips taken with the same src, dest, and equipment
        self.routes = self.routes_filtered.groupby(self.routes_filtered.columns.to_list(), as_index=False).size()
        self.routes.rename(columns={'size': 'count'}, inplace=True)

    def _select_plane_color(self, plane, color):
        if color:
            return color
        if plane == '300':
            color = 'rgb(255, 0, 0)'
        elif plane == '319':
            color = 'rgb(128, 0, 0)'
        elif plane == '320':
            color = 'rgb(255, 255, 0)'
        elif plane == '321':
            color = 'rgb(128, 128, 0)'
        elif plane == '727':
            color = 'rgb(0, 255, 0)'
        elif plane == '737':
            color = 'rgb(0, 128, 0)'
        elif plane == '757':
            color = 'rgb(0, 255, 255)'
        elif plane == '767':
            color = 'rgb(0, 128, 128)'
        elif plane == '777':
            color = 'rgb(0, 0, 255)'
        elif plane == 'D10':
            color = 'rgb(0, 0, 128)'
        elif plane == 'S80':
            color = 'rgb(255, 0, 255)'
        return color

    def _update_map_center(self, airport_list):

        if not airport_list:
            return
        routes = pd.DataFrame()
        for airport in airport_list:
            routes = pd.concat([routes, self.airports[self.airports['IATA'].isin([airport])]]).reset_index(drop=True)
        print(routes)

        lat = 0
        lon = 0
        for i in range(len(routes)):

            print(routes['IATA'][i])
            print(routes['Latitude'][i])
            print(routes['Longitude'][i])
            lat = lat + routes['Latitude'][i]
            lon = lon + routes['Longitude'][i]
        lat = lat/len(routes)
        lon = lon/len(routes)
        print(lat)
        print(lon)
        self.map.update_geos(
           center=dict(lon=lon, lat=lat),
        )


    def _draw_base_map(self):
        self.map = go.Figure(go.Scattergeo())
        self.map.update_layout(go.Layout(
            showlegend = False,
            autosize=True,
            paper_bgcolor = 'rgb(29, 29, 29)',
            plot_bgcolor = 'rgb(29, 29, 29)',
           # height=700,
           # margin={"r":0,"t":0,"l":0,"b":0},

        ))
        self.map.update_geos(
            scope='world',
            resolution=50,
            #projection=dict( type='orthographic' , scale = 1.8),
            projection=dict( type='equal earth' , scale = 1.8),
            #projection=dict( type='orthographic' , scale = 1),
            showland = True,
            showocean = True,
            visible=False,
            showlakes = False,
            showsubunits = True,
            showcoastlines = True,
            showcountries = True,
            landcolor = 'rgb(49, 49, 49)',
            countrycolor = 'rgb(90, 90, 90)',
            subunitcolor = 'rgb(90, 90, 90)',
            subunitwidth = 3,
            coastlinecolor = 'rgb(90, 90, 90)',
            oceancolor = 'rgb(29, 29, 29)',
            bgcolor = 'rgb(29, 29, 29)',
        )

    def _populate_airport_trace(self):
        airports = self.airports
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
                #sizemin=4,
                size=(self.airports['total count']/max(self.airports['total count']))*30 + 5,
                color='red',
                line = dict(
                    width=1,
                    color='rgb(0, 0, 0)'
                ),
                opacity = 1,
            ),
        ))

    def _populate_route_traces(self, equipment, color):
        for i in range(len(self.routes)):
            color = self._select_plane_color(self.routes['Equipment'][i], color)
            self.map.add_trace(go.Scattergeo(
                type = 'scattergeo',
                locationmode = 'ISO-3',
                showlegend = True,
                name = str(self.routes['Equipment'][i]),
                hoverinfo='skip',
                #text = "{} <-> {}: {}".format(self.routes['Source airport'][i], self.routes['Destination airport'][i], self.routes['count'][i]),
                lon = [self.routes['Longitude_Orig'][i], self.routes['Longitude_Dest'][i]],
                lat = [self.routes['Latitude_Orig'][i], self.routes['Latitude_Dest'][i]],
                mode = 'lines',
                line = dict(
                    width=max((self.routes['count'][i]/max(self.routes['count']))*5, 0.25),
                    color=color
                )
            ))
if __name__ == "__main__":
    main()
