#!/usr/bin/python
# -*- coding: utf-8 -*-

import plotly
import pandas as pd
import plotly.plotly as py
import plotly.graph_objs as go
import dash
import dash_core_components as dcc
import dash_html_components as html
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

plotly.tools.set_credentials_file(username='penny.sun', api_key='aBIJh98JIvQGpELF9qOv')

# download file
def partial(total_byte_len, part_size_limit):
    s = []
    for p in range(0, total_byte_len, part_size_limit):
        last = min(total_byte_len - 1, p + part_size_limit - 1)
        s.append([p, last])
    return s

def GD_download_file(service, file_id):
    drive_file = service.files().get(fileId=file_id).execute()
    download_url = drive_file.get('downloadUrl')
    total_size = int(drive_file.get('fileSize'))
    s = partial(total_size, 100000000) # I'm downloading BIG files, so 100M chunk size is fine for me
    title = drive_file.get('title')
    originalFilename = drive_file.get('originalFilename')
    filename = './' + originalFilename
    if download_url:
        with open(filename, 'wb') as file:
            print("Bytes downloaded: ")
            for bytes in s:
                headers = {"Range" : 'bytes=%s-%s' % (bytes[0], bytes[1])}
                resp, content = service._http.request(download_url, headers=headers)
                if resp.status == 206 :
                    file.write(content)
                    file.flush()
                else:
                    print('An error occurred: %s' % resp)
                    return None
                print(str(bytes[1])+"...")
        return title, filename
    else:
        return None

gauth = GoogleAuth()
#gauth.CommandLineAuth() #requires cut and paste from a browser
gauth.LocalWebserverAuth()

FILE_ID = '12hw86e62G9P3MT15o16tcQmqiZYJMFBq'

drive = GoogleDrive(gauth)
service = gauth.service
#file = drive.CreateFile({'id':FILE_ID})    # Use this to get file metadata
title, filename = GD_download_file(service, FILE_ID)


df = pd.read_csv(filename, encoding='utf-8', dtype=object)

#station
station_group = df.groupby('station')
station_group_cnt = df.groupby('station', as_index=False).size().reset_index(name='counts').sort_values('counts', ascending=True)
stations = station_group_cnt['station'].values.tolist()
stations_cnt = station_group_cnt['counts'].values.tolist()
#time
times = pd.DatetimeIndex(df.dt)
hr_group = df.groupby(times.hour)
hr_group_cnt = df.groupby(times.hour, as_index=False).size().reset_index(name='counts')
hrs = hr_group_cnt['dt'].values.tolist()
hrs_cnt = hr_group_cnt['counts'].values.tolist()

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.Div([
        html.Label('Enable filter'),
        dcc.RadioItems(
            id='filter-type',
            options=[{'label': i, 'value': i} for i in ['All','Time', 'Station']],
            value='All',
            labelStyle={'display': 'inline-block'}
        )
    ], style={'width': '50%', 'float': 'left', 'display': 'inline-block'}),
    html.Div([
        dcc.Graph(
            id='userprofile-piechart'
        )
    ], style={'width': '100%', 'display': 'inline-block','padding': '0 10'}),
    html.Div([
        html.Div([
            dcc.Graph(
                id='hr-count-barchart',
                figure={
                    'data':[{
                        'x': hrs,
                        'y': hrs_cnt,
                        'type': 'bar'
                    }]
                }
            )
        ], style={'width': '49%', 'display': 'inline-block'}),
        html.Div([
            dcc.Graph(
                id='station-count-barchart',
                figure={
                    'data':[{
                        'x': stations_cnt,
                        'y': stations,
                        'type': 'bar',
                        'orientation': 'h'
                    }]
                }
            )
        ], style={'width': '49%', 'float': 'right', 'display': 'inline-block'})
    ])
])


#update graph
@app.callback(
    dash.dependencies.Output('userprofile-piechart','figure'),
    [dash.dependencies.Input('station-count-barchart','hoverData'),
     dash.dependencies.Input('hr-count-barchart', 'hoverData'),
     dash.dependencies.Input('filter-type', 'value')])
def update_peichart(s_hoverData, h_hoverData, filter_type):
    if filter_type == 'Time':
        if not h_hoverData:
            filter_name = 'All Day'
            df_filtered = df
        else:
            filter_name = h_hoverData['points'][0]['x']
            df_filtered = hr_group.get_group(filter_name)
    elif filter_type == 'Station':
        if not s_hoverData:
            filter_name = 'All Stations'
            df_filtered = df
        else:
            filter_name = s_hoverData['points'][0]['y']
            df_filtered = station_group.get_group(filter_name)
    else:
        filter_name = 'data'
        df_filtered = df

    df_uu = df_filtered.drop_duplicates(subset=['mid', 'locale', 'region', 'app_type', 'sex', 'age_range', 'area'])

    categories = ['sex', 'age_range', 'app_type']

    x = [[0, .3], [.35, .65], [.7, 1]]
    y = [[0, 1], [0, 1], [0, 1]]

    fig = {}
    data = []
    for i, category in enumerate(categories):
        fig_data = {}
        grouped = df_uu.groupby(category, as_index=False).agg({'mid': 'count'}).sort_values(by=['mid'], ascending=False)
        fig_data['labels'] = grouped[category].values.tolist()
        fig_data['values'] = grouped['mid'].values.tolist()
        fig_data['type'] = 'pie'
        fig_data['name'] = category
        fig_data['domain'] = {'x': x[i], 'y': y[i]}
        fig_data['hoverinfo'] = 'all'
        fig_data['textinfo'] = 'percent'
        data.append(fig_data)

    fig['data'] = data
    fig['layout'] = {'title': 'LINE Beacon MRT User Profile: %d UU in %s %s' % (len(df_uu), filter_type, filter_name),
                     'showlegend': True}
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
