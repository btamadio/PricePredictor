#!/usr/bin/env python
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
import pandas as pd
import math
import csv
import pprint
import json
def dist_to_ferry(lat,lon):
    ferry = (37.795623,-122.393439)
    result = (lat-ferry[0])*(lat-ferry[0])+(lon-ferry[1])*(lon-ferry[1])
    return math.sqrt(result)
    
def transformDataFrame(df):
    df=df.drop('page',1,errors='ignore')
    df=df.dropna()
    df=df[df.price < 1000]
    df['log_dist_ferry']=df.apply(lambda x:1/dist_to_ferry(x['lat'],x['lon']),axis=1)
    df['bed_futon'] = df['bed_type'].apply(lambda x: x=='Futon')
    df['bed_real'] = df['bed_type'].apply(lambda x: x=='Real Bed')
    df['bed_air'] = df['bed_type'].apply(lambda x: x=='Airbed')
    df['bed_sofa'] = df['bed_type'].apply(lambda x:x=='Pull-out Sofa')
    df['bed_couch'] = df['bed_type'].apply(lambda x: x=='Couch')
    df['private_room'] = df['room_type'].apply(lambda x: x=='Private room')
    df['entire_home'] = df['room_type'].apply(lambda x: x=='Entire home/apt')
    df['shared_room'] = df['room_type'].apply(lambda x: x=='Shared room')
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
        for (price_min,price_max) in [(0,40),(41,45),(46,50),(51,55),(56,59),(60,61),(62,63),(64,65),(66,68),(69,70),(71,73),(74,75),(76,78),(79,80),(81,85),(86,90),(91,95),(96,100),(101,150),(151,200),(201,-1)]:
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
        f = open(out_file,'w')
        idList = []
        for roomID in self.scrapeRoomIDs(city_name,room_type):
            if not roomID in idList:
                idList.append(roomID)
                f.write(roomID+'\n')
    def scrapeRooms(self,room_file,out_file):
        room_list = []
        with open(room_file) as f:
            for line in f:
                room_list.append(line.rstrip())
        with open(out_file,'w') as csvFile:
            writer = csv.writer(csvFile,delimiter=';')
            headers = ['room_id','acc_rating','bed_type','cancel_policy','checkin_rating',
                       'cleanliness_rating','communication_rating','guest_sat','hosting_id',
                       'instant_book','is_superhost','loc_rating','lat','lon','page','person_cap',
                       'pic_count','room_type','saved_to_wishlist_count','value_rating','rev_count','price','star_rating']
            for i in range(1,51):
                headers.append('amen_'+str(i))
            writer.writerow(headers)
            for room_id in room_list:
                line = self.scrapeRoom(room_id)
                if len(line) > 0:
                    writer.writerow(line)                
    def scrapeRoom(self,room_id):
        url = 'https://www.airbnb.com/rooms/'+room_id
        print('Scraping room info from ',url)
        featDict = {'room_id':room_id}
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
                featDict['review_score'] = listing_dict['listing']['review_details_interface']['review_score']
                featDict['host_other_rev_count'] = listing_dict['listing']['review_details_interface']['host_other_property_review_count']
                featDict['review_count'] = listing_dict['listing']['review_details_interface']['review_count']
#                pprint.pprint(listing_dict['listing']['review_details_interface']['review_score'])
#                pprint.pprint(listing_dict['listing']['space_interface'])
            meta = soup.find('meta',id='_bootstrap-room_options')
            if not meta:
                return {}
            dict0 = json.loads(meta.get('content'))
            if not dict0:
                return {}
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
                
                #df['log_dist_ferry']=df.apply(lambda x:1/dist_to_ferry(x['lat'],x['lon']),axis=1)
                
                featDict['private_room'] = (dataDict['room_type'] == 'Private room')
                featDict['entire_home'] = (dataDict['room_type'] =='Entire home/apt')
                featDict['shared_room'] = (dataDict['room_type'] =='Shared room')
                
                for i in range(1,51):
                    featDict['amen_'+str(i)] = i in amenList
                return featDict
            else:
                return {}
        except:
            return {}

c = cityScraper()
pprint.pprint(c.scrapeRoom('16297659'))
