#!/usr/bin/env python
from cityScraper import cityScraper
c=cityScraper()
#c.writeRoomIDs('San-Francisco--CA','Private%20room','data/SF_roomList_private_3.txt')
c.scrapeRooms('data/SF_roomList_private_3.txt','data/SF_data_private_6.csv')
