#! /usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import re
from BeautifulSoup import BeautifulSoup
from datetime import date


def get_data(url):
    day = getDayStr()
    if not day:
        return None

    data = requests.get(url).text
    try:
        data = data.split('<table width="100%" border="0" cellspacing="10" cellpadding="0">')[1]
        data = data.split('<td colspan="2">%s</td>' % day)[1]
        data = data.split('<tr class="huomio">')[0]
    except IndexError:
        return None
    return data


def getDayStr():
    days = {0: 'Maanantai', 1: 'Tiistai', 2: 'Keskiviikko', 3: 'Torstai', 4: 'Perjantai'}
    day = date.today()

    if date.weekday(day) not in days:
        return

    day_name = days[date.weekday(day)]
    dayStr = '%s %i.%i' % (day_name, day.day, day.month)

    return dayStr


def make_dict(source):
    soup = BeautifulSoup(source)
    foods = dict()
    p = re.compile(r'<.*?>')
    foodstr = soup.findAll('td', attrs={'height': '35', 'align': 'left', 'valign': 'bottom'})
    for tmp_food in foodstr:
        tmp_food = '%s' % tmp_food
        name = tmp_food.split('</small></b><br />')[0]
        food = tmp_food.split('</small></b><br />')[1].split('<br /><i><small>')[0]

        name = p.sub('', name).strip()
        food = p.sub('', food).strip().strip('¤')
        foods[name] = food
    return foods


def make_text(data):
    text = ''
    for k, v in data.iteritems():
        text += '%s: %s | ' % (k, v)
    return text


def command_kurnis(bot, user, channel, args):
    url = 'http://www.aalef.fi/ruokalistat.php'
    data = get_data(url)
    if not data:
        return bot.say(channel, 'Ei ruokalistaa tälle päivälle')

    data = make_dict(data)
    text = make_text(data)
    if not text:
        return bot.say(channel, 'Ei ruokalistaa tälle päivälle')
    return bot.say(channel, text)
