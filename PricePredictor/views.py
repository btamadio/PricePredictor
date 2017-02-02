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
       title = 'AirBnB Deal Finder')
@app.route('/',methods=['POST'])
def find_suggestions():
    num_results = 5
    featureList = joblib.load('PricePredictor/static/featureList_binary_v1.pkl')
    dbList = joblib.load('PricePredictor/static/dbList_binary_v1.pkl')
    importance_dict = joblib.load('PricePredictor/static/importance_dict_v1.pkl')
    amen_name_dict = joblib.load('PricePredictor/static/amen_name_dict.pkl')


    c=cityScraper()
    featureDict = c.scrapeRoom(request.form['text'].strip())
    max_dist = float(request.form['dist'].strip())
    room_id = str(featureDict['room_id'])
    res= {'room_id':room_id,'max_dist':max_dist}
    selected_df = pd.DataFrame(featureDict,index=[int(room_id)])
    selected_df = selected_df[dbList]
    list_price = int(selected_df['price'].iloc[0].strip('$'))
    loc = (selected_df['lat'].iloc[0],selected_df['lon'].iloc[0])
    print('Querying database for room info')
    dbname = 'airbnb_db'
    username = 'postgres'
    pswd = 'abc123'
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
    max_price = list_price
    full_df = full_df[full_df.price < max_price]
    full_df = full_df[full_df.index != int(res['room_id'])]
    print('Calculating feature vectors')
    def getFeatureVec(d):
        return [int(d[i]) for i in featureList]
    def sim_dist(v1,v2):
        if len(v1) != len(v2):
            print ('Error: mismatched feature vectors')
            sys.exit(1)
        i=0
        res = 0
        for key in sorted(importance_dict):
            if key != featureList[i]:
                print ('Error: mismatched feature names')
                print (importance_dict[key],featureList[i])
                sys.exit(1)
            res += (v1[i]-v2[i])*importance_dict[key]*(v1[i]-v2[i])
            i+=1
        return math.sqrt(res)
    full_df['feature_vec'] = full_df.apply(getFeatureVec,1)

    selected_df['feature_vec'] = selected_df.apply(getFeatureVec,1)
    print('Calculating similarity distance')
    full_df['sim_dist'] = full_df['feature_vec'].apply(lambda x:sim_dist(x,selected_df['feature_vec'].values[0]))
    cancel_dict = {3:'Flexible',4:'Moderate',5:'Strict'}
    # #list the 10 most similar in order of price
    full_df = full_df.sort('sim_dist',ascending=1).head(num_results)#.sort('price',ascending=1)
    full_df['ind'] = full_df.index
    full_df['price'] = full_df['price'].apply( lambda x : '${0:.0f}'.format(x) )
    full_df['distance'] = full_df['distance'].apply( lambda x : '{0:.2f}'.format(x) )
    full_df['person_cap'] = full_df['person_cap'].apply(lambda x: int(x))
    full_df['guest_sat'] = full_df['guest_sat'].apply(lambda x: int(x))
    full_df['num_beds'] = full_df['num_beds'].apply(lambda x:int(x))
    full_df['cable_tv'] = full_df['amen_2'].apply(lambda x:'Yes' if x else 'No')
    full_df['tv'] = full_df['amen_1'].apply(lambda x:'Yes' if x else 'No')
    full_df['cancel_policy'] = full_df['cancel_policy'].apply( lambda x: cancel_dict[x])
    full_df['cleanliness_rating'] = full_df['cleanliness_rating'].apply(lambda x: int(x))
    full_df['family_friendly'] = full_df['amen_31'].apply(lambda x:'Yes' if x else 'No')
    full_df['kitchen'] = full_df['amen_8'].apply(lambda x:'Yes' if x else 'No')
    full_df['parking'] = full_df['amen_9'].apply(lambda x:'Yes' if x else 'No')
    full_df['internet'] = full_df['amen_3'].apply(lambda x:'Yes' if x else 'No')

#    selected_df['price'] = selected_df['price'].apply( lambda x : '${0:.0f}'.format(x) )
#    selected_df['distance'] = selected_df['distance'].apply( lambda x : '{0:.2f}'.format(x) )
    selected_df['person_cap'] = selected_df['person_cap'].apply(lambda x: int(x))
    selected_df['guest_sat'] = selected_df['guest_sat'].apply(lambda x: int(x))
    selected_df['num_beds'] = selected_df['num_beds'].apply(lambda x:int(x))
    selected_df['cable_tv'] = selected_df['amen_2'].apply(lambda x:'Yes' if x else 'No')
    selected_df['tv'] = selected_df['amen_1'].apply(lambda x:'Yes' if x else 'No')
    selected_df['cancel_policy'] = selected_df['cancel_policy'].apply( lambda x: cancel_dict[x])
    selected_df['cleanliness_rating'] = selected_df['cleanliness_rating'].apply(lambda x: int(x))
    selected_df['family_friendly'] = selected_df['amen_31'].apply(lambda x:'Yes' if x else 'No')
    selected_df['kitchen'] = selected_df['amen_8'].apply(lambda x:'Yes' if x else 'No')
    selected_df['parking'] = selected_df['amen_9'].apply(lambda x:'Yes' if x else 'No')
    selected_df['internet'] = selected_df['amen_3'].apply(lambda x:'Yes' if x else 'No')

    res['suggestions'] = full_df.head(num_results).to_dict('records')
    res['this_room'] = selected_df.to_dict('records')

    return render_template("results.html",
       title = 'AirBnB Price Predictor',
       result = res)
