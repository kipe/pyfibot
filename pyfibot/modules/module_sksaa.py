#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests

userid = None
token = None
url = None
sensors = None


def init(bot):
    global userid
    global token
    global url
    global sensors
    config = bot.config.get("module_sksaa", {})
    userid = config.get("userid", "")
    token = config.get("token", "")
    url = config.get("url", "")
    sensors = config.get("sensors", "")


def command_sksaa(bot, user, channel, args):
    if userid and token and url and sensors:
        data = requests.get(url, params={'user': userid, 'token': token}).json()
        sensordata = []
        for s in data['data']:
            if s['pk'] in sensors:
                sensordata.append(u'%s: %.1f°C' % (s['fields']['name'], s['fields']['last_temperature']))
        return bot.say(channel, 'Or4: %s' % ', '.join(sensordata))
    return bot.say(channel, '".sksaa" toistaiseksi pois käytöstä, kokeile ".saa"')
