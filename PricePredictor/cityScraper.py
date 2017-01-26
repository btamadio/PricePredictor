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
import psycopg2

def dist_to_ferry(lat,lon):
    ferry = (37.795623,-122.393439)
    result = (lat-ferry[0])*(lat-ferry[0])+(lon-ferry[1])*(lon-ferry[1])
    return math.sqrt(result)
    
def transformDataFrame(df):
    df=df.dropna()
    df=df.drop(['room_type','hosting_id'],errors='ignore')
    df=df[df.price < 300]
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
                {'is_castle':'Castle'}]
    for cat in room_cat:
        key = list(cat.keys())[0]
        df[key] = df['prop_type'].apply(lambda x:x==cat[key])
    df=df.drop('prop_type',1)
    df['num_bathrooms']=df['num_bathrooms'].apply(lambda x:int(x[0]))
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
        url = 'https://www.airbnb.com/rooms/'+room_id
        print('Scraping room info from ',url)
        featDict = {'is_apt':False,'is_house':False,'is_other':False,'is_tent':False,'is_townhouse':False,'is_villa':False}
        try:
            req = Request(url,headers={'User-Agent':'Mozilla/5.0'})
            page = urlopen(req).read()
            soup = BeautifulSoup(page,"lxml")
            listing = soup.find('meta',id='_bootstrap-listing')
            if listing:
                listing_dict = json.loads(listing.get('content'))
                for d in listing_dict['listing']['space_interface']:
                    if d['label'] == 'Bathrooms:':
                        featDict['num_bathrooms'] = d['value']
                    if d['label'] == 'Bedrooms:':
                        featDict['num_bedrooms'] = d['value']
                    if d['label'] == 'Beds:':
                        featDict['num_beds'] = d['value']
                    if d['label'] == 'Property type:':
                        featDict['prop_type'] = d['value']
                        featDict['is_apt'] = (d['value'] == 'Apartment')
                        featDict['is_house'] = (d['value'] == 'House')
                        featDict['is_other'] = (d['value'] == 'Other')
                        featDict['is_tent'] = (d['value'] == 'Tent')
                        featDict['is_townhouse'] = (d['value'] == 'Townhouse')
                        featDict['is_villa'] = (d['value'] == 'Villa')
                featDict['review_score'] = listing_dict['listing']['review_details_interface']['review_score']
                featDict['host_other_rev_count'] = listing_dict['listing']['review_details_interface']['host_other_property_review_count']
                featDict['review_count'] = listing_dict['listing']['review_details_interface']['review_count']
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
                        featDict['acc_rating'] = dataDict['accuracy_rating']
                        featDict['cancel_policy'] = dataDict['cancel_policy']
                        featDict['checkin_rating'] = dataDict['checkin_rating']
                        featDict['cleanliness_rating'] = dataDict['cleanliness_rating']
                        featDict['communication_rating'] = dataDict['communication_rating']
                        featDict['guest_sat'] = dataDict['guest_satisfaction_overall']
                        featDict['hosting_id'] = dataDict['hosting_id']
                        featDict['instant_book'] = dataDict['instant_book_possible']
                        featDict['is_superhost'] = dataDict['is_superhost']
                        featDict['loc_rating'] = dataDict['location_rating']
                        featDict['lat'] = dataDict['listing_lat']
                        featDict['lon'] = dataDict['listing_lng']
                        featDict['dist_ferry']=dist_to_ferry(featDict['lat'],featDict['lon'])
                        featDict['person_cap'] = dataDict['person_capacity']
                        featDict['pic_count'] = dataDict['picture_count']
                        featDict['price'] = dataDict['price']
                        featDict['saved_to_wishlist_count'] = dataDict['saved_to_wishlist_count']
                        featDict['value_rating'] = dataDict['value_rating']
                        featDict['bed_futon'] = (dataDict['bed_type'] == 'Futon')
                        featDict['bed_real'] = (dataDict['bed_type'] == 'Real Bed')
                        featDict['bed_air'] = (dataDict['bed_type'] == 'Airbed')
                        featDict['bed_sofa'] = (dataDict['bed_type'] == 'Pull-out Sofa')
                        featDict['bed_couch'] = (dataDict['bed_type'] == 'Couch')
                
                        featDict['private_room'] = (dataDict['room_type'] == 'Private room')
                        featDict['entire_home'] = (dataDict['room_type'] =='Entire home/apt')
                        featDict['shared_room'] = (dataDict['room_type'] =='Shared room')
                
                        for i in range(1,51):
                            featDict['amen_'+str(i)] = (i in amenList)
            return featDict
        except:
            return {}
