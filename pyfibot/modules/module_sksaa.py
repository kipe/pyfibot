#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests

userid = None
token = None
url = None


def init(bot):
    global userid
    global token
    global url
    config = bot.config.get("module_sksaa", {})
    userid = config.get("userid", "")
    token = config.get("token", "")
    url = config.get("url", "")


def command_sksaa(bot, user, channel, args):
    if userid and token and url:
        data = requests.get(url, params={'user': userid, 'token': token}).json()['data'][0]['fields']
        tempStr = '%.1f °c (%s)' % (data['last_temperature'], data['last_temperature_time'][:16].encode('utf-8'))
        return bot.say(channel, tempStr)
    return None
