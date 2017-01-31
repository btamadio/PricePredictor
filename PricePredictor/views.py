from flask import render_template
from flask import request
from PricePredictor import app
from PricePredictor.cityScraper import cityScraper
from PricePredictor.cityScraper import transformDataFrame
from scipy.spatial.distance import cosine
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
    max_dist = 1.0
    featureList = joblib.load('PricePredictor/static/featureList_binary_v1.pkl')
    dbList = joblib.load('PricePredictor/static/dbList_binary_v1.pkl')

    res= {'room_id':request.form['text'].strip()}
    c=cityScraper()
    featureDict = c.scrapeRoom(res['room_id'])
    selected_df = pd.DataFrame(featureDict,index=[int(res['room_id'])])
    selected_df = selected_df[dbList]
#    print(selected_df[dbList].dtypes)
    list_price = int(selected_df['price'].iloc[0].strip('$'))
    loc = (selected_df['lat'].iloc[0],selected_df['lon'].iloc[0])
    print('Querying database for room info')
    dbname = 'airbnb_db'
    username = 'brian'
    pswd = ''
    engine = create_engine('postgresql://%s:%s@localhost/%s'%(username,pswd,dbname))
    con = None
    con = psycopg2.connect(database = dbname, user = username, host='localhost', password=pswd)

    sql_query = 'SELECT * FROM binary_table;'
    full_df = pd.read_sql_query(sql_query,con,index_col='index')
    full_df['loc'] = full_df[['lat','lon']].apply(tuple,axis=1)

    print('Calculating distances')
    #calculate distance between our listing and all others
    full_df['distance'] = full_df['loc'].apply( lambda x: vincenty(x,loc).miles )
    full_df = full_df[full_df.distance < max_dist]
    max_price = 1.1*list_price
    full_df = full_df[full_df.price < max_price]
    full_df = full_df[full_df.index != int(res['room_id'])]
    if selected_df['person_cap'].values[0] > 1:
        full_df = full_df[full_df.person_cap > 1]
    print('Calculating feature vectors')
    def getFeatureVec(d):
        return [int(d[i]) for i in featureList]
    full_df['feature_vec'] = full_df.apply(getFeatureVec,1)
    selected_df['feature_vec'] = selected_df.apply(getFeatureVec,1)
    print('Calculating similarity distance')
    full_df['sim_dist'] = full_df['feature_vec'].apply(lambda x:cosine(x,selected_df['feature_vec'].values[0]))

    # #list the 5 most similar in order of price
    full_df = full_df.sort('sim_dist',ascending=1).head(5).sort('price',ascending=1)
    full_df['ind'] = full_df.index
    full_df['price'] = full_df['price'].apply( lambda x : '${0:.0f}'.format(x) )
    full_df['distance'] = full_df['distance'].apply( lambda x : '{0:.2f}'.format(x) )
    full_df['person_cap'] = full_df['person_cap'].apply(lambda x: int(x))
    full_df['cleanliness_rating'] = full_df['cleanliness_rating'].apply(lambda x: int(x))
    full_df['guest_sat'] = full_df['guest_sat'].apply(lambda x: int(x))
    full_df['num_beds'] = full_df['num_beds'].apply(lambda x:int(x))
    res['suggestions'] = full_df.head(6).to_dict('records')
    res['this_room'] = selected_df.to_dict('records')

    return render_template("results.html",
       title = 'Home',
       result = res)
