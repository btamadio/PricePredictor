from flask import render_template
from flask import request
from PricePredictor import app
from PricePredictor.cityScraper import cityScraper
from PricePredictor.cityScraper import transformDataFrame
import pandas as pd
import math
import sys
from sklearn.externals import joblib
import os
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
import psycopg2
from geopy.distance import vincenty
from pprint import pprint

@app.route('/')
def index():
   return render_template("index.html",
       title = 'AirBnB Price Predictor')
@app.route('/',methods=['POST'])
def my_form_post():
    res= {'room_id':request.form['text'].strip()}
    c=cityScraper()
    featureDict = c.scrapeRoom(res['room_id'])
    df = transformDataFrame(pd.DataFrame(featureDict,index=[0]))
    forest = joblib.load('PricePredictor/static/forest_v1.pkl')
    featureList = joblib.load('PricePredictor/static/featureList_v1.pkl')
    pred_price = forest.predict(df[featureList])[0]
    list_price = df['price'][0]
    loc = (df['lat'][0],df['lon'][0])
    res['pred'] = pred_price
    res['listed'] = list_price
    
    if res['pred'] < res['listed']:
        res['isDeal'] = 'Bad'
    else:
        res['isDeal'] = 'Good'
    
    dbname = 'airbnb_db'
    username = 'brian'
    pswd = ''
    engine = create_engine('postgresql://%s:%s@localhost/%s'%(username,pswd,dbname))
    con = None
    con = psycopg2.connect(database = dbname, user = username, host='localhost', password=pswd)

    sql_query = 'SELECT index,pred_price,price,lat,lon FROM city_table;'
    airbnb_df = pd.read_sql_query(sql_query,con,index_col='index')
    airbnb_df['loc'] = airbnb_df[['lat','lon']].apply(tuple,axis=1)

    #calculate distance between our listing and all others
    airbnb_df['distance'] = airbnb_df['loc'].apply( lambda x: vincenty(x,loc).miles )
    airbnb_df = airbnb_df[airbnb_df.distance < 1]
    airbnb_df = airbnb_df[airbnb_df.index != int(res['room_id'])]

    #calculate similarity between our listing and all others
    airbnb_df['sim_dist'] = airbnb_df['pred_price'].apply( lambda x: abs(x - pred_price) )
    
    #list the 5 most similar in order of price
    airbnb_df = airbnb_df.sort('sim_dist',ascending=1).head(5).sort('price',ascending=1)
    airbnb_df['ind'] = airbnb_df.index
    
    airbnb_df['price'] = airbnb_df['price'].apply( lambda x : '${0:.2f}'.format(x) )
    airbnb_df['distance'] = airbnb_df['distance'].apply( lambda x : '{0:.2f}'.format(x) )
    res['suggestions'] = airbnb_df.head(5).to_dict('records')
    return render_template("results.html",
       title = 'Home',
       result = res)
