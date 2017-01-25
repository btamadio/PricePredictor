from flask import render_template
from flask import request
from PricePredictor import app
from PricePredictor.cityScraper import cityScraper
import pandas as pd
import math
from sklearn.externals import joblib
import os

@app.route('/')
def index():
   user = { 'nickname': 'Brian' } 
   return render_template("index.html",
       title = 'Home',
       user = user,
       result = '')
@app.route('/',methods=['POST'])
def my_form_post():
    user = { 'nickname': 'Brian' } 
    text = request.form['text']
    c=cityScraper()
    featureDict = c.scrapeRoom(text)
    df = pd.DataFrame(featureDict,index=[0])
    df = df.dropna()
    df = df.drop('page',1)

    def dist_to_ferry(lat,lon):
        ferry = (37.795623,-122.393439)
        result = (lat-ferry[0])*(lat-ferry[0])+(lon-ferry[1])*(lon-ferry[1])
        return math.sqrt(result)
    df['log_dist_ferry']=df.apply(lambda x:math.log(1/dist_to_ferry(x['lat'],x['lon'])),axis=1)
    df['bed_futon'] = df['bed_type'].apply(lambda x: x=='Futon')
    df['bed_real'] = df['bed_type'].apply(lambda x: x=='Real Bed')
    df['bed_air'] = df['bed_type'].apply(lambda x: x=='Airbed')
    df['bed_sofa'] = df['bed_type'].apply(lambda x:x=='Pull-out Sofa')
    df['bed_couch'] = df['bed_type'].apply(lambda x: x=='Couch')
    df['private_room'] = df['room_type'].apply(lambda x: x=='Private room')
    df['entire_home'] = df['room_type'].apply(lambda x: x=='Entire home/apt')
    featureList=['room_id',
 'acc_rating',
 'cancel_policy',
 'checkin_rating',
 'cleanliness_rating',
 'communication_rating',
 'guest_sat',
 'hosting_id',
 'instant_book',
 'is_superhost',
 'loc_rating',
 'lat',
 'lon',
 'person_cap',
 'pic_count',
 'saved_to_wishlist_count',
 'value_rating',
 'rev_count',
 'star_rating',
 'amen_1',
 'amen_2',
 'amen_3',
 'amen_4',
 'amen_5',
 'amen_6',
 'amen_7',
 'amen_8',
 'amen_9',
 'amen_10',
 'amen_11',
 'amen_12',
 'amen_13',
 'amen_14',
 'amen_15',
 'amen_16',
 'amen_17',
 'amen_18',
 'amen_19',
 'amen_20',
 'amen_21',
 'amen_22',
 'amen_23',
 'amen_24',
 'amen_25',
 'amen_26',
 'amen_27',
 'amen_28',
 'amen_29',
 'amen_30',
 'amen_31',
 'amen_32',
 'amen_33',
 'amen_34',
 'amen_35',
 'amen_36',
 'amen_37',
 'amen_38',
 'amen_39',
 'amen_40',
 'amen_41',
 'amen_42',
 'amen_43',
 'amen_44',
 'amen_45',
 'amen_46',
 'amen_47',
 'amen_48',
 'amen_49',
 'amen_50',
 'log_dist_ferry',
 'bed_futon',
 'bed_real',
 'bed_air',
 'bed_sofa',
 'bed_couch',
 'private_room',
 'entire_home']

    forest = joblib.load('PricePredictor/static/forest_v1.pkl')
    pred_price = forest.predict(df[featureList])[0]
    return render_template("index.html",
       title = 'Home',
       user = user,
       result = pred_price)
