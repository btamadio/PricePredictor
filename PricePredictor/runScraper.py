#!/usr/bin/env python
from cityScraper import cityScraper
c=cityScraper()
#c.writeRoomIDs('San-Francisco--CA','Private%20room','data/SF_roomList_private_3.txt')
#c.scrapeRooms('data/SF_roomList_private_3.txt','data/SF_data_private_6.csv')
#roomList = [7367530,14938407,9414733,7143032,8685570,8685716,8554141]
#i=0
# with open('data/SF_roomList_private_3.txt') as f:
#     for line in f:
#         if i%100 == 0:
#             c.scrapeRoom(line)
#         i+=1
#        print (line.rstrip())
#for room in roomList:
#    c.scrapeRoom(str(room))
c.scrapeRoom('https://www.airbnb.com/rooms/14549750?s=thbT0Z9D')
