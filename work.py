# -*- coding: utf-8 -*-
from __future__ import print_function
import httplib2
import os
import time
import datetime
import itertools
from operator import itemgetter
from pymongo import MongoClient



def main():

	client = MongoClient('localhost', 27017)
	db = client['calendar-data']
	mongo_calendars = db.calendars
	empty = mongo_calendars.count() == 0
	print ('Base is empty:', empty)
	print("Welcome to your personal planner!")
	print("You can choose between these calendars:")
	num_list = mongo_calendars.find()
	count = 0
	for cal in num_list:
		print(cal['summary'], count)
		count+=1
	print("---------- 1 ----------")
	print("       STATISTICS")
	print("-----------------------")
	var = int(input("Choose your calendar number [0,1,2...n]\n"))
	calendar_list = mongo_calendars.find()
	calendar = calendar_list[var]
	print (calendar['summary'], " is chosen")
	
	days = int(input("How many days do you want to see? [1,2...]\n"))
	today = datetime.datetime.now().date() # utc - формат
	print('now is ', today)
	events = calendar['events']
	events.sort(key=itemgetter('start'))
	for i in itertools.repeat(None, days):
		tomorrow = today + datetime.timedelta(days=1)
		for event in events:
			overflow = False
			start_date = datetime.datetime.strptime(event['start'][:16], "%Y-%m-%dT%H:%M")
			if start_date.date() >= today and start_date.date() < tomorrow:
				overflow = True
				end_date = datetime.datetime.strptime(event['end'][:16], "%Y-%m-%dT%H:%M")
				print('\tevent \"'+event['title']+'\" from [', event['start'], '] for [', end_date - start_date, ']')
			else:
				if overflow is True:
					break;
		today = tomorrow
		print('next is', today)

	print("---------- 2 ----------")
	print("     INTERSECTION")
	print("-----------------------")

	first = int(input("Choose your first calendar number [0,1,2...n]\n"))
	second = int(input("Choose your second calendar number [0,1,2...n]\n"))
	first_times = []
	second_times = []
	calendar_list = mongo_calendars.find()

	first_calendar = calendar_list[first]
	first_events = first_calendar['events']
	for event in first_events:
		time_tuple = datetime.datetime.strptime(event['start'][:19], "%Y-%m-%dT%H:%M:%S"), datetime.datetime.strptime(event['end'][:19], "%Y-%m-%dT%H:%M:%S")
		first_times.append(time_tuple)
	first_times.sort(key=itemgetter(0))

	second_calendar = calendar_list[second]
	second_events = second_calendar['events']
	for event in second_events:
		time_tuple = datetime.datetime.strptime(event['start'][:19], "%Y-%m-%dT%H:%M:%S"), datetime.datetime.strptime(event['end'][:19], "%Y-%m-%dT%H:%M:%S")
		second_times.append(time_tuple)
	second_times.sort(key=itemgetter(0))

	intersections = []
	for time1 in first_times:
		for time2 in second_times:
			t_from = time2[0]
			t_to = time2[1]
			if time1[0] > time2[0]:
				t_from = time1[0]
			if time1[1] < time2[1]:
				t_to = time1[1]
			difference = t_to - t_from
			if difference.total_seconds() > 0:
				intersection_tuple = t_from, t_to, difference
				intersections.append(intersection_tuple)
	intersections.sort(key=itemgetter(0))
	for stamp in intersections:
		print(stamp[0], '--', stamp[1], '[', stamp[2], ']')

	print("-------optimized--------")
	length = len(intersections)-1
	i = 0
	while i<length:
		j = i+1
		if intersections[j][0] <= intersections[i][0] and intersections[j][1] >= intersections[i][1]:
			del intersections[i]
			length-=1
			i=-1
		else:
			if intersections[i][0] <= intersections[j][0] and intersections[i][1] >= intersections[j][1]:
				del intersections[j]
				length-=1
				i=-1
			else:
				if intersections[j][0] < intersections[i][0] and intersections[j][1] > intersections[i][0]:
					new_tuple = intersections[j][0],intersections[i][1],intersections[i][1]-intersections[j][0]
					intersections.append(new_tuple)
					del intersections[i]
					del intersections[j]
					length-=1
					i=-1
				else:
					if intersections[j][0] < intersections[i][1] and intersections[j][1] > intersections[i][1]:
						new_tuple = intersections[i][0],intersections[j][1],intersections[j][1]-intersections[i][0]
						intersections.append(new_tuple)
						del intersections[i]
						del intersections[j]
						length-=1
						i=-1
		i+=1
	for stamp in intersections:
		print(stamp[0], '--', stamp[1], '[', stamp[2], ']')
	print("---------- 3 ----------")
	print("       PLANNING")
	print("-----------------------")
	day_events = 0
	date = input("Choose your date [year-month-day][2017-12-30]\n")
	date_stamp = datetime.datetime.strptime(date[:10], "%Y-%m-%d").date()
	for stamp in intersections:
		if stamp[0].date() == date_stamp:
			day_events -= stamp[2].total_seconds()
	print(day_events/3600, 'hours of total intersections')
	
	length = len(first_times)-1
	i=0
	first_sum = 0
	while i<length:
		if first_times[i][0].date() == date_stamp:
			if first_times[i][0] < first_times[i+1][0] and first_times[i][1] > first_times[i+1][1]:
				del first_times[i+1]
				length -= 1
				i-=1
			else:
				if first_times[i][1] > first_times[i+1][0] and first_times[i][1] < first_times[i+1][1]:
					new_tuple = first_times[i][0], first_times[i+1][1]
					del first_times[i]
					del first_times[i]
					first_times.insert(i, new_tuple)
					length -= 1
					i-=1
		i+=1
	for time in first_times:
		if time[0].date() == date_stamp:
			first_sum += (time[1] - time[0]).total_seconds()		

	length = len(second_times)-1
	i=0
	second_sum = 0
	while i<length:
		if second_times[i][0].date() == date_stamp:
			if second_times[i][0] < second_times[i+1][0] and second_times[i][1] > second_times[i+1][1]:
				del second_times[i+1]
				length -= 1
				i-=1
			else:
				if second_times[i][1] > second_times[i+1][0] and second_times[i][1] < second_times[i+1][1]:
					new_tuple = second_times[i][0], second_times[i+1][1]
					del second_times[i]
					del second_times[i]
					second_times.insert(i, new_tuple)
					length -= 1
					i-=1	
		i+=1
	for time in second_times:
		if time[0].date() == date_stamp:
			second_sum += (time[1] - time[0]).total_seconds()	

	print((first_sum+second_sum)/3600, 'hours of events total')	
	total_time = (day_events + first_sum + second_sum)/3600
	if 24-total_time <= 0:
		print ('sorry, you have no time left')
	else:
		print (24 - total_time, 'hours is free that day')

if __name__ == '__main__':
	main()