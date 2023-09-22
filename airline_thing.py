#!/usr/bin/env python3
import argparse, re

import pandas as pd
import numpy as np
import plotly.offline as py
import plotly.graph_objs as go
from matplotlib import colors as mcolors

height = 4000
width = 4000

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--airports_file", help="airports.csv to use", required=True)
    parser.add_argument("--routes_file", help="routes.csv to use", required=True)
    parser.add_argument("-e", "--equipment", nargs='+',help="planes to generate data for", required=False)
    parser.add_argument("-a", "--airports", nargs='+', help="airports to generate data for", required=False)
    parser.add_argument("-r", "--roles", help="role to generate data for (Captain, First Officer)", required=False)
    parser.add_argument("-c", "--color", help="uniform color to use for routes", required=False)
    parser.add_argument("-s", "--scope", help="world, north america, usa", required=False)
    parser.add_argument("--center", help="uniform color to use for routes", required=False)
    parser.add_argument("--generate", help="generate files", action='store_true',required=False)

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

    if not args.scope:
        args.scope = 'world'

    if args.generate:
        data.generate_files()
    else:
        data.show_map(args.equipment, args.color, args.airports, args.roles, args.scope, args.center)


class AirlineData:
    def __init__(self, airports_file, routes_file, airport_list=None):
        self.airports_raw = pd.read_csv(airports_file)
        self.routes_raw = pd.read_csv(routes_file)

        self.routes_filtered= pd.DataFrame()
        self.airports_filtered= pd.DataFrame()

        self.routes = pd.DataFrame()
        self.airports = pd.DataFrame()

        self._import_data()

    def generate_files(self):
        print("737")
        self.save_image(['737'], None, None, ['CA','RC','FO','FB','FC'], 'north america', 'usa', './imgs/737.svg')
        print("757")
        self.save_image(['757'], None, None, ['CA','RC','FO','FB','FC'], 'north america', 'usa', './imgs/757.svg')
        print("767")
        self.save_image(['767'], None, None, ['CA','RC','FO','FB','FC'], 'world', 'JFK', './imgs/767.svg')
        print("777")
        self.save_image(['777'], None, None, ['CA','RC','FO','FB','FC'], 'world', 'JFK', './imgs/777.svg')
        self.save_image(['737', '757', '767', '777'], None, None, ['CA','RC','FO','FB','FC'], 'world', 'JFK', './imgs/all_routes.svg')
        self.save_image(['737', '757', '767', '777'], None, None, ['CA','RC'], 'world', 'JFK', './imgs/all_routes_captain.svg')
        self.save_image(['737', '757', '767', '777'], None, None, ['FO','FB','FC'], 'world', 'JFK', './imgs/all_routes_first_officer.svg')

    def save_image(self, equipment, color, airport_list, roles, scope, center, filename):
        self._filter_and_generate(equipment, color, airport_list, roles, scope, center)
        self.map.write_image(filename, width=width, height=height)

    def show_map(self, equipment, color, airport_list, roles, scope, center):
        self._filter_and_generate(equipment, color, airport_list, roles, scope, center)
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

    def _filter_and_generate(self, equipment, color, airport_list, roles, scope, center):
        self.routes_filtered = self.routes_raw
        self.airports_filtered = self.airports_raw
        self._filter_routes_by_airport(airport_list)
        self._filter_routes_by_plane(equipment)
        self._filter_routes_by_role(roles)

        self._count_airport_visits()
        self._count_route_frequency()

        self._draw_base_map()
        self._update_map_center(scope, center)
        self._populate_route_traces(equipment, color)
        self._populate_airport_trace()

        self.map.write_image('test.svg',width=width, height=height)
        #print(self.airports.to_string())
        #print(self.routes)

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
        self.airports = self.airports.loc[self.airports['total count'] > 0.1].reset_index()

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
            color = '#697282'
        elif plane == '757':
            color = '#EE2A24'
        elif plane == '767':
            color = '#D90429'
        elif plane == '777':
            color = '#003876'
        elif plane == 'D10':
            color = 'rgb(0, 0, 128)'
        elif plane == 'S80':
            color = 'rgb(255, 0, 255)'
        return color

    def _update_map_center(self, scope, center):
        if not center:
            lon = 0
        if center == 'usa':
            lon = -98.5795
        elif center == 'JFK':
            lon = -73.778900
        if scope == 'world':
            subdiv = False
            countries = True
        elif scope == 'north america':
            subdiv = True
            countries = True
        elif scope == 'usa':
            subdiv = True
            countries = False
        self.map.update_geos(
            projection_rotation=dict(lon=lon, lat=0, roll=0),
            scope = scope,
            showsubunits = subdiv,
            showcountries = countries,
        )

    def _draw_base_map(self):
        self.map = go.Figure(go.Scattergeo())

        self.map.update_layout(go.Layout(
            showlegend = False,
            autosize=True,
            height=800,
            #paper_bgcolor = 'rgb(29, 29, 29)',
            #plot_bgcolor = 'rgb(29, 29, 29)',
            #height=700,
            #margin={"r":0,"t":0,"l":0,"b":0},

        ))
        #ocean = '#E6E6E6' #grey
        ocean = '#9EDAFF' #blue
        #ocean = '#DAF1FF' #different blue
        self.map.update_geos(
            resolution=50,
            projection=dict( type='equal earth'),
            showocean = True,
            oceancolor = ocean,
            showlakes = True,
            lakecolor = ocean,
            showsubunits = True,
            showcoastlines = True,
            showcountries = True,
            countrycolor = 'rgb(90, 90, 90)',
            subunitcolor = 'rgb(90, 90, 90)',
        )

    def state_sample(self):
        fig = go.Figure(go.Scattergeo())
        print("sample town")
        fig.update_geos(
            visible=False, resolution=50, scope="north america",
            showcountries=True, countrycolor="Black",
            showsubunits=True, subunitcolor="Blue"
        )
        fig.update_layout(height=300, margin={"r":0,"t":0,"l":0,"b":0})
        fig.show()

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
                size=(self.airports['total count']/max(self.airports['total count']))*40 + 10,
                color='rgb(0, 56, 118)',
                line = dict(
                    width=0,
                    color='red'
                ),
                opacity = 1,
            ),
        ))

    def _populate_route_traces(self, equipment, default_color):
        for i in range(len(self.routes)):
            color = self._select_plane_color(self.routes['Equipment'][i], default_color)
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
                    width=(self.routes['count'][i]/max(self.routes['count']))*7 + 0.75,
                    color=color
                )
            ))
if __name__ == "__main__":
    main()
