from flask import render_template
from flask import request
from PricePredictor import app
from PricePredictor.cityScraper import cityScraper
from PricePredictor.cityScraper import transformDataFrame
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
    df = transformDataFrame(pd.DataFrame(featureDict,index=[0]))
    featureList = sorted(list(df.drop(['price','room_type','bed_type'],1)))
    forest = joblib.load('PricePredictor/static/forest_v1.pkl')
    pred_price = forest.predict(df[featureList])[0]
    return render_template("index.html",
       title = 'Home',
       user = user,
       result = pred_price)
