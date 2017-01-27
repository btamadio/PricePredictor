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
    df = transformDataFrame(pd.DataFrame(featureDict,index=[int(res['room_id'])]))
#    print(df.head())
    forest = joblib.load('PricePredictor/static/forest_v1.pkl')
    featureList = joblib.load('PricePredictor/static/featureList_v1.pkl')
    pred_price = forest.predict(df[featureList])[0]
    list_price = int(df['price'].iloc[0].strip('$'))
    loc = (df['lat'].iloc[0],df['lon'].iloc[0])
    res['pred'] = '${0:.2f}'.format(pred_price)
    res['listed'] = '${0:.2f}'.format(list_price)
    
    if pred_price < list_price:
        res['isDeal'] = 'Bad'
    else:
        res['isDeal'] = 'Good'
    
    dbname = 'airbnb_db'
    username = 'brian'
    pswd = ''
    engine = create_engine('postgresql://%s:%s@localhost/%s'%(username,pswd,dbname))
    con = None
    con = psycopg2.connect(database = dbname, user = username, host='localhost', password=pswd)

    sql_query = 'SELECT * FROM city_table;'
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
    
    airbnb_df['price'] = airbnb_df['price'].apply( lambda x : '${0:.0f}'.format(x) )
    airbnb_df['distance'] = airbnb_df['distance'].apply( lambda x : '{0:.2f}'.format(x) )
    airbnb_df['review_score'] = airbnb_df['review_score'].apply( lambda x: str(int(x)) )
    airbnb_df['person_cap'] = airbnb_df['person_cap'].apply(lambda x: int(x))
    airbnb_df['cleanliness_rating'] = airbnb_df['cleanliness_rating'].apply(lambda x: int(x))
    airbnb_df['guest_sat'] = airbnb_df['guest_sat'].apply(lambda x: int(x))
    res['suggestions'] = airbnb_df.head(6).to_dict('records')
    res['this_room'] = df.to_dict('records')

    room_cat = [{'is_loft':'Loft'},
                {'is_condo':'Condominium'},
                {'is_bnb':'Bed & Breakfast'},
                {'is_guesthouse':'Guesthouse'},
                {'is_cabin':'Cabin'},
                {'is_lighthouse':'Lighthouse'},
                {'is_dorm':'Dorm'},
                {'is_bungalow':'Bungalow'},
                {'is_bout_hotel':'Boutique hotel'},
                {'is_treehouse':'Treehouse'},
                {'is_timeshare':'Timeshare'},
                {'is_hostel':'Hostel'},
                {'is_chalet':'Chalet'},
                {'is_boat':'Boat'},
                {'is_cave':'Cave'},
                {'is_castle':'Castle'},
                {'is_apt':'Apartment'},
                {'is_house':'House'},
                {'is_other':'Other'},
                {'is_tent':'Tent'},
                {'is_townhouse':'Townhouse'},
                {'is_villa':'Villa'}]
    for cat in room_cat:
        key = list(cat.keys())[0]
        for sugg in res['suggestions']:
            if sugg[key]:
                sugg['prop_type'] = cat[key]
        if res['this_room'][0][key]:
            res['this_room'][0]['prop_type'] = cat[key]
    
    return render_template("results.html",
       title = 'Home',
       result = res)
