#!/usr/bin/env python
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
import pandas as pd
import math
import csv
import pprint
import json
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from sklearn.externals import joblib
import psycopg2

def dist_to_ferry(lat,lon):
    ferry = (37.795623,-122.393439)
    result = (lat-ferry[0])*(lat-ferry[0])+(lon-ferry[1])*(lon-ferry[1])
    return math.sqrt(result)
def transformDataFrame(df):
    df=df.dropna()
    temp_df = df
    df['num_bathrooms']=temp_df['num_bathrooms'].apply(lambda x:float(str(x).strip('+')))
    temp_df = df
    df['is_apt'] = df['prop_type'].apply(lambda x: x=='Apartment')
    for i in range(1,51):
        key = 'amen_'+str(i)
        if key in df:
            df[key] = temp_df[key].apply(bool)#lambda x:bool(x))
    temp_df = df
    df['instant_book'] = temp_df['instant_book'].apply(lambda x:bool(x))
    df = df.drop(['prop_type'],1)

    threshDict = {'acc_rating':9,'cancel_policy':4,'checkin_rating':9,'cleanliness_rating':9,'communication_rating':9,'guest_sat':95,'host_other_rev_count':0,'loc_rating':9,'num_bathrooms':0.5,'num_beds':1,'person_cap':1,'pic_count':26,'value_rating':9}
    for key in threshDict:
        df['bin_'+key] = df[key].apply( lambda x:x>threshDict[key] )
    df['bin_review_count'] = df['review_count'].apply(lambda x:(x>6 and x<30))
    df['bin_is_apt'] = df['is_apt']
    df['bin_instant_book'] = df['instant_book']
    return df

class cityScraper:
    def __init__(self):
        pass
    def getLastPage(self,city_name,room_type,price_min,price_max):
        url = self.getURL(city_name,room_type,price_min,price_max,1)
        req = Request(url,headers={'User-Agent':'Mozilla/5.0'})
        page = urlopen(req).read()
        soup = BeautifulSoup(page,"lxml")
        lastPage = 1
        for link in soup.find_all('a'):
            href = link.get('href')
            if not href:
                continue
            if '/s/'+city_name+'?page=' in href:
                pageLink = int(href.split('=')[1])
                if pageLink > lastPage:
                    lastPage = pageLink
        return lastPage
    def scrapeRoomIDs(self,city_name,room_type):
        priceMinList = [0]+list(range(41,100))+list(range(100,200,5))+[200]
        priceMaxList = list(range(40,100))+list(range(104,201,5))+[-1]
        for i in range(len(priceMinList)):
            price_min = priceMinList[i]
            price_max = priceMaxList[i]
            lastPage = self.getLastPage(city_name,room_type,price_min,price_max)
            for page_num in range(1,lastPage+1):
                url = self.getURL(city_name,room_type,price_min,price_max,page_num)
                print('scraping room IDs from %s' % url)
                req = Request(url,headers={'User-Agent':'Mozilla/5.0'})
                page = urlopen(req).read()
                soup = BeautifulSoup(page,"lxml")
                all_links = soup.find_all('a')
                for link in all_links:
                    href = link.get('href')
                    if href:
                        if '/rooms/' in href and not 'new?' in href:
                            room_id = int(href.split('/')[2])
                            yield str(room_id)
    def getURL(self,city_name,room_type,price_min,price_max,page_num):
        if price_max > 0:
            url= 'https://www.airbnb.com/s/'+city_name+'?room_types[]='+room_type+'&price_min='+str(price_min)+'&price_max='+str(price_max)+'&page='+str(page_num)
        else:
            url= 'https://www.airbnb.com/s/'+city_name+'?room_types[]='+room_type+'&price_min='+str(price_min)+'&page='+str(page_num)
        return url
    def writeRoomIDs(self,city_name,room_type,out_file):
        idList = []
        for roomID in self.scrapeRoomIDs(city_name,room_type):
            f = open(out_file,'a')
            if not roomID in idList:
                idList.append(roomID)
                f.write(roomID+'\n')
    def scrapeRooms(self,room_file,out_file):
        dbname = 'airbnb_db'
        username = 'brian'
        pswd = ''
        room_list = []
        with open(room_file) as f:
            for line in f:
                room_list.append(line.rstrip())
        f=open(out_file,'w')
        df = pd.DataFrame(self.scrapeRoom(room_list[0]),index=[int(room_list[0])])
        df.to_csv(f)
        f.close()
        for room_id in room_list:
            f=open(out_file,'a')
            df=df.append(pd.DataFrame(self.scrapeRoom(room_id),index=[int(room_id)]))
            df[df.index==int(room_id)].to_csv(f,header=False)
            f.close()
    def scrapeRoom(self,room_id):
        url = room_id
        if not 'airbnb.com' in room_id:
            url = 'https://www.airbnb.com/rooms/'+room_id
        print('Scraping room info from ',url)
        featDict = {}

        try:
            req = Request(url,headers={'User-Agent':'Mozilla/5.0'})
            page = urlopen(req).read()
            soup = BeautifulSoup(page,"lxml")
            room_options = soup.find('meta',id='_bootstrap-room_options')
            if (room_options):
                room_opt_dict = json.loads(room_options.get('content'))
                featDict['price'] = room_opt_dict['nightly_price']
            else:
                featDict['price'] = '0'
            listing = soup.find('meta',id='_bootstrap-listing')
            if listing:
                listing_dict = json.loads(listing.get('content'))
                featDict['room_id'] = listing_dict['listing']['id']
                for d in listing_dict['listing']['space_interface']:
                    if d['label'] == 'Bathrooms:':
                        featDict['num_bathrooms'] = float(d['value'])
                    if d['label'] == 'Beds:':
                        featDict['num_beds'] = int(d['value'])
                    if d['label'] == 'Property type:':
                        featDict['is_apt'] = (d['value'] == 'Apartment')
                        featDict['bin_is_apt'] = int(d['value'] == 'Apartment')
                featDict['host_other_rev_count'] = int(listing_dict['listing']['review_details_interface']['host_other_property_review_count'])
                featDict['review_count'] = int(listing_dict['listing']['review_details_interface']['review_count'])

            meta = soup.find('meta',id='_bootstrap-room_options')
            if not meta:
                pass
            else:
                dict0 = json.loads(meta.get('content'))
                if not dict0:
                    pass
                else:
                    dataDict = dict0['airEventData']
                    if dataDict:
                        amenList = dataDict['amenities']
                        featDict['acc_rating'] = int(dataDict['accuracy_rating'])
                        featDict['cancel_policy'] = int(dataDict['cancel_policy'])
                        featDict['checkin_rating'] = int(dataDict['checkin_rating'])
                        featDict['cleanliness_rating'] = int(dataDict['cleanliness_rating'])
                        featDict['communication_rating'] = int(dataDict['communication_rating'])
                        featDict['guest_sat'] = int(dataDict['guest_satisfaction_overall'])
                        featDict['instant_book'] = int(dataDict['instant_book_possible'])
                        featDict['bin_instant_book'] = int(dataDict['instant_book_possible'])
                        featDict['loc_rating'] = int(dataDict['location_rating'])
                        featDict['lat'] = float(dataDict['listing_lat'])
                        featDict['lon'] = float(dataDict['listing_lng'])
                        featDict['person_cap'] = int(dataDict['person_capacity'])
                        featDict['pic_count'] = int(dataDict['picture_count'])
                        if featDict['price'] == 0:
                            featDict['price'] = dataDict['price']
                        featDict['value_rating'] = dataDict['value_rating']
                        for i in range(1,51):
                            featDict['amen_'+str(i)] = int(i in amenList)
            threshDict = {'acc_rating':9,'cancel_policy':4,'checkin_rating':9,'cleanliness_rating':9,'communication_rating':9,'guest_sat':95,'host_other_rev_count':0,'loc_rating':9,
                          'num_bathrooms':0.5,'num_beds':1,'person_cap':1,'pic_count':26,'value_rating':9}                            
            for key in threshDict:
                featDict['bin_'+key] = int(featDict[key] > threshDict[key])
            featDict['bin_review_count'] = int(featDict['review_count'] > 6 and featDict['review_count'] < 30)
            return featDict
        except:
            return {}
