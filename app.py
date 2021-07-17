# Simple demo app only
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.graph_objs as go
import settings
import itertools
import math
import base64
from flask import Flask
import os
import psycopg2
import datetime
import re
import nltk

nltk.download('punkt')
nltk.download('stopwords')
from nltk.probability import FreqDist
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from textblob import TextBlob
from joblib import load
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = 'Real-Time Twitter Monitor'

server = app.server

app.layout = html.Div(children=[
    html.H2('Real-time Twitter Sentiment Analysis for Depression ', style={
        'textAlign': 'center'
    }),
    html.H4('(Omar project)', style={
        'textAlign': 'right'
    }),

    html.Div(id='live-update-graph'),
    html.Div(id='live-update-graph-bottom'),

    # Author's Words
    html.Div(
        className='row',
        children=[
            dcc.Markdown(
                "final year project"),
        ], style={'width': '35%', 'marginLeft': 70}
    ),
    html.Br(),

    # ABOUT ROW
    html.Div(
        className='row',
        children=[
            html.Div(
                className='three columns',
                children=[
                    html.P(
                        'Data extracted from:'
                    ),
                    html.A(
                        'Twitter API',
                        href='https://developer.twitter.com'
                    )
                ]
            ),
            html.Div(
                className='three columns',
                children=[
                    html.P(
                        'Code avaliable at:'
                    ),
                    html.A(
                        'GitHub',
                        href='not yet put it later'
                    )
                ]
            ),
            html.Div(
                className='three columns',
                children=[
                    html.P(
                        'Made with:'
                    ),
                    html.A(
                        'Dash / Plot.ly',
                        href='https://plot.ly/dash/'
                    )
                ]
            ),
            html.Div(
                className='three columns',
                children=[
                    html.P(
                        'Author:'
                    ),
                    html.A(
                        'Omar'
  #                      href='later'
                    )
                ]
            )
        ], style={'marginLeft': 70, 'fontSize': 16}
    ),

    dcc.Interval(
        id='interval-component-slow',
        interval=1 * 10000,  # in milliseconds
        n_intervals=0
    )
], style={'padding': '20px'})


# Multiple components can update everytime interval gets fired.
@app.callback(Output('live-update-graph', 'children'),
              [Input('interval-component-slow', 'n_intervals')])
def update_graph_live(n):
    # Loading data from Heroku PostgreSQL
    DATABASE_URL = os.environ['DATABASE_URL']
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
   # query = "SELECT id_str, text, created_at, polarity, user_location, user_followers_count FROM {}".format(
   #     settings.TABLE_NAME)
    #timenow = (datetime.datetime.utcnow() - datetime.timedelta(hours=0, minutes=20)).strftime('%Y-%m-%d %H:%M:%S')
    query = "SELECT id_str, text, created_at, depression, user_location, user_followers_count FROM {}".format(settings.TABLE_NAME)
    df = pd.read_sql(query, con=conn)

    # Convert UTC into BST
    df['created_at'] = pd.to_datetime(df['created_at']).apply(lambda x: x - datetime.timedelta(hours=1))

    # Clean and transform data to enable time series
    result = df.groupby([pd.Grouper(key='created_at', freq='10s'), 'depression']).count().unstack(
        fill_value=0).stack().reset_index()
    result = result.rename(
        columns={"id_str": "Num of '{}' mentions".format(settings.TRACK_WORDS[0]), "created_at": "Time in BTS"})
    time_series = result["Time in BTS"][result['depression'] == 'positive' or 'negative'].reset_index(drop=True)

    min10 = datetime.datetime.now() - datetime.timedelta(hours=1, minutes=10)
    min20 = datetime.datetime.now() - datetime.timedelta(hours=1, minutes=20)

    neg_num = result[result['Time'] > min10]["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][
        result['depression'] == 'negative'].sum()
    pos_num = result[result['Time'] > min10]["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][
        result['depression'] == 'positive'].sum()

    # Loading back-up summary data
#    query = "SELECT daily_user_num, daily_tweets_num, impressions FROM Back_Up;"
#    back_up = pd.read_sql(query, con=conn)
#    daily_tweets_num = back_up['daily_tweets_num'].iloc[0] + result[-6:-3]["Num of '{}' mentions".format(settings.TRACK_WORDS[0])].sum()
#    daily_impressions = back_up['impressions'].iloc[0] + df[df['created_at'] > (datetime.datetime.now() - datetime.timedelta(hours=7, seconds=10))]['user_followers_count'].sum()
#    cur = conn.cursor()

#    PDT_now = datetime.datetime.now() - datetime.timedelta(hours=7)
#    if PDT_now.strftime("%H%M")=='0000':
#        cur.execute("UPDATE Back_Up SET daily_tweets_num = 0, impressions = 0;")
#    else:
#        cur.execute("UPDATE Back_Up SET daily_tweets_num = {}, impressions = {};".format(daily_tweets_num, daily_impressions))
#    conn.commit()
#    cur.close()
#    conn.close()

    # Percentage Number of Tweets changed in Last 10 mins

    count_now = df[df['created_at'] > min10]['id_str'].count()
    count_before = df[(min20 < df['created_at']) & (df['created_at'] < min10)]['id_str'].count()
    percent = (count_now - count_before) / count_before * 100
    # Create the graph
    children = [
        html.Div([
            html.Div([
                dcc.Graph(
                    id='crossfilter-indicator-scatter',
                    figure={
                        'data': [
                            go.Scatter(
                                x=time_series,
                                y=result["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][
                                    result['depression'] == 0].reset_index(drop=True),
                                name="Neutrals",
                                opacity=0.8,
                                mode='lines',
                                line=dict(width=0.5, color='rgb(131, 90, 241)'),
                                stackgroup='one'
                            ),

                            go.Scatter(
                                x=time_series,
                                y=result["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][
                                    result['depression'] == 'negative'].reset_index(drop=True).apply(lambda x: -x),
                                name="Negatives",
                                opacity=0.8,
                                mode='lines',
                                line=dict(width=0.5, color='rgb(255, 50, 50)'),
                                stackgroup='two'
                            ),
                            go.Scatter(
                                x=time_series,
                                y=result["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][
                                    result['depression'] == 'positive'].reset_index(drop=True),
                                name="Positives",
                                opacity=0.8,
                                mode='lines',
                                line=dict(width=0.5, color='rgb(184, 247, 212)'),
                                stackgroup='three'
                            )
                        ]
                    }
                )
            ], style={'width': '73%', 'display': 'inline-block', 'padding': '0 0 0 20'}),

            html.Div([
                dcc.Graph(
                    id='pie-chart',
                    figure={
                        'data': [
                            go.Pie(
                                labels=['Positives', 'Negatives'],
                                values=[pos_num, neg_num],
                                name="View Metrics",
                                marker_colors=['rgba(255, 50, 50, 0.6)', 'rgba(184, 247, 212, 0.6)'],
                                textinfo='value',
                                hole=.65)
                        ],
                        'layout': {
                            'showlegend': False,
                            'title': 'Tweets In Last 10 Mins',
                            'annotations': [
                                dict(
                                    text='{0:.1f}K'.format((pos_num + neg_num) / 1000),
                                    font=dict(
                                        size=40
                                    ),
                                    showarrow=False
                                )
                            ]
                        }

                    }
                )
            ], style={'width': '27%', 'display': 'inline-block'})
        ]),

        html.Div(
            className='row',
            children=[
                html.Div(
                    children=[
                        html.P('Tweets/10 Mins Changed By',
                               style={
                                   'fontSize': 17
                               }
                               ),
                        html.P('{0:.2f}%'.format(percent) if percent <= 0 else '+{0:.2f}%'.format(percent),
                               style={
                                   'fontSize': 40
                               }
                               )
                    ],
                    style={
                        'width': '20%',
                        'display': 'inline-block'
                    }

                ),



                html.Div(
                    children=[
                        html.P(
                            "Currently tracking the word depression on twitter",
                            style={
                                'fontSize': 25
                            }
                            ),
                    ],
                    style={
                        'width': '40%',
                        'display': 'inline-block'
                    }
                ),

            ],
            style={'marginLeft': 70}
        )
    ]
    return children


@app.callback(Output('live-update-graph-bottom', 'children'),
              [Input('interval-component-slow', 'n_intervals')])
def update_graph_bottom_live(n):
    # Loading data from Heroku PostgreSQL
    DATABASE_URL = os.environ['DATABASE_URL']
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    query = "SELECT id_str, text, created_at, depression, user_location, user_followers_count FROM {}".format(settings.TABLE_NAME)
    df = pd.read_sql(query, con=conn)
    conn.close()

    # Convert UTC into PDT
    df['created_at'] = pd.to_datetime(df['created_at']).apply(lambda x: x - datetime.timedelta(hours=7))

    # Clean and transform data to enable word frequency
    content = ' '.join(df["text"])
    content = re.sub(r"http\S+", "", content)
    content = content.replace('RT ', ' ').replace('&amp;', 'and')
    content = re.sub('[^A-Za-z0-9]+', ' ', content)
    content = content.lower()

    # Filter constants for states in europe
    STATES = ['Albania', 'ALB', 'Andorra', 'AND', 'Armenia', 'ARM', 'Austria', 'AUT', 'Belarus', 'BLR', 'Belgium', 'BEL', 'Bosnia and Herzegovina', 'BIH', 'Bulgaria', 'BGR', 'Croatia',
              'HRV', 'Cyprus', 'CYP', 'Czech Republic', 'CZE', 'Denmark', 'DNK', 'Estonia', 'EST', 'Finland', 'FIN', 'France', 'FRA', 'United Kingdom of Great Britain and Northern Ireland', 'GBR', 'Georgia',
              'GEO', 'Germany', 'DEU', 'Faroe Islands', 'FRO', 'Greece', 'GRC', 'Gibraltar', 'GIB', 'Hungary', 'HUN', 'Iceland', 'ISL', 'Ireland', 'IRL', 'Italy', 'ITA', 'Latvia', 'LVA', 'Liechtenstein',
              'LIE', 'Lithuania', 'LTU', 'Luxembourg', 'LUX', 'North Macedonia', 'MKD', 'Malta', 'MLT', 'Republic of Moldova', 'MDA', 'Monaco', 'MCO', 'Montenegro', 'MNE', 'Netherlands', 'NLD', 'Norway',
              'NOR', 'Poland', 'POL', 'Portugal', 'PRT', 'Romania', 'ROU', 'Russian Federation', 'RUS', 'San Marino', 'SMR', 'Serbia', 'SRB', 'Slovakia', 'SVK', 'Slovenia', 'SVN', 'Spain', 'ESP', 'Sweden',
              'SWE', 'Switzerland', 'CHE', 'Turkey', 'TUR',  'Ukraine', 'UKR']
    STATE_DICT = dict(itertools.zip_longest(*[iter(STATES)] * 2, fillvalue=""))
    INV_STATE_DICT = dict((v, k) for k, v in STATE_DICT.items())

    # Clean and transform data to enable geo-distribution
    is_in_Europe = []
    geo = df[['user_location']]
    df = df.fillna(" ")
    for x in df['user_location']:
        check = False
        for s in STATES:
            if s in x:
                is_in_Europe.append(STATE_DICT[s] if s in STATE_DICT else s)
                check = True
                break
        if not check:

            is_in_Europe.append(None)

    geo_dist = pd.DataFrame(is_in_Europe, columns=['State']).dropna().reset_index()
    geo_dist = geo_dist.groupby('State').count().rename(columns={"index": "Number"}) \
        .sort_values(by=['Number'], ascending=False).reset_index()
    geo_dist["Log Num"] = geo_dist["Number"].apply(lambda x: math.log(x, 2))

    geo_dist['Full State Name'] = geo_dist['State'].apply(lambda x: INV_STATE_DICT[x])
    geo_dist['text'] = geo_dist['Full State Name'] + '<br>' + 'Num: ' + geo_dist['Number'].astype(str)

    tokenized_word = word_tokenize(content)
    stop_words = set(stopwords.words("english"))
    filtered_sent = []
    for w in tokenized_word:
        if (w not in stop_words) and (len(w) >= 3):
            filtered_sent.append(w)
    fdist = FreqDist(filtered_sent)
    fd = pd.DataFrame(fdist.most_common(16), columns=["Word", "Frequency"]).drop([0]).reindex()
    fd['depression'] = fd['Word'].apply(lambda x: TextBlob(x).sentiment.polarity)
    fd['Marker_Color'] = fd['depression'].apply(lambda x: 'rgba(255, 50, 50, 0.6)' if x < -0.1 else \
        ('rgba(184, 247, 212, 0.6)' if x > 0.1 else 'rgba(131, 90, 241, 0.6)'))
    fd['Line_Color'] = fd['depression'].apply(lambda x: 'rgba(255, 50, 50, 1)' if x < -0.1 else \
        ('rgba(184, 247, 212, 1)' if x > 0.1 else 'rgba(131, 90, 241, 1)'))



    # Create the graph
    children = [
        html.Div([
            dcc.Graph(
                id='x-time-series',
                figure={
                    'data': [
                        go.Bar(
                            x=fd["Frequency"].loc[::-1],
                            y=fd["Word"].loc[::-1],
                            name="Neutrals",
                            orientation='h',
                            marker_color=fd['Marker_Color'].loc[::-1].to_list(),
                            marker=dict(
                                line=dict(
                                    color=fd['Line_Color'].loc[::-1].to_list(),
                                    width=1),
                            ),
                        )
                    ],
                    'layout': {
                        'hovermode': "closest"
                    }
                }
            )
        ], style={'width': '49%', 'display': 'inline-block', 'padding': '0 0 0 20'}),
        html.Div([
            dcc.Graph(
                id='y-time-series',
                figure={
                    'data': [
                        go.Choropleth(
                            locations=geo_dist['State'],  # Spatial coordinates
                            z=geo_dist['Log Num'].astype(float),  # Data to be color-coded
                            locationmode="ISO-3",  # set of locations match entries in `locations`
                            # colorscale = "Blues",
                            text=geo_dist['text'],  # hover text
                            geo='geo',
                            colorbar_title="Num in Log2",
                            marker_line_color='white',
                            colorscale=["#fdf7ff", "#835af1"],
                            # autocolorscale=False,
                            # reversescale=True,
                        )
                    ],
                    'layout': {
                        'title': "Geographic seg for Europe",
                        'geo': {'scope': 'europe'}
                    }
                }
            )
        ], style={'display': 'inline-block', 'width': '49%'})
    ]

    return children


if __name__ == '__main__':
    app.run_server(debug=True)

