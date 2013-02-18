#! /usr/bin/env python
# -*- coding: utf-8 -*-
import requests
from datetime import date


def make_dicts(data):
    foods = list()
    for c in data['courses']:
        foods.append((c['category'], c['title_fi']))
    return foods


def make_text(foods):
    text = ''
    for food in foods:
        text += '%s: %s | ' % (food[0].encode('utf-8'), food[1].encode('utf-8'))
    text = text.rstrip(' | ')
    return text


def command_sotku(bot, user, channel, args):
    '''Fetches Sodexo Universitys foods for today.'''
    today = date.today()
    place = 441
    if args == 'amk':
        place = 472

    url = "http://www.sodexo.fi/ruokalistat/output/daily_json/%i/%s/%s/%s/fi" % (place, today.year, today.month, today.day)
    data = requests.get(url).json()
    if not 'courses' in data:
        return bot.say(channel, 'Ei ruokalistaa tälle päivälle')
    foods = make_dicts(data)
    text = make_text(foods)
    return bot.say(channel, text)
