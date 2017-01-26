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
    airbnb_df = pd.read_sql_query(sql_query,con)
    airbnb_df['loc'] = airbnb_df[['lat','lon']].apply(tuple,axis=1)
    airbnb_df['distance'] = airbnb_df['loc'].apply( lambda x: vincenty(x,loc).miles )
    airbnb_df['sim_dist'] = airbnb_df['pred_price'].apply( lambda x: abs(x - pred_price) )
    airbnb_df = airbnb_df.sort('sim_dist',ascending=1).head(5).sort('price',ascending=1)
    
    print(airbnb_df.head())
    res['suggestions'] = airbnb_df.head(5).to_dict('records')
    return render_template("results.html",
       title = 'Home',
       result = res)
