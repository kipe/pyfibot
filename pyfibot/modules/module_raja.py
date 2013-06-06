# -*- encoding: utf-8 -*-
import requests
import json
from datetime import datetime, timedelta


def get_data():
    try:
        r = requests.get('http://granitsa-online.com/Pages/Splash.aspx', cookies={'CurCulNam': 'en-EN'})
        if r.status_code == 200:
            data = r.text.split("'Cars': ")[1].split("'Trucks': {")[0].replace('\t', '').replace('\n', '').replace('\r', '').replace('\'', '"').rstrip(',')
            return json.loads(data)
    except:
        return


def make_string(data, direction):
    updateTime = datetime.now() + timedelta(days=2)
    for k, v in data[direction].iteritems():
        up = datetime.strptime(v['Update'], 'Update time: %m/%d/%Y at %I:%M:%S %p')
        up = up.replace(hour=up.hour - 1)
        if up < updateTime:
            updateTime = up

    nuijamaa = u'Nuijamaa: %s' % (data[direction]['NuijBrus']['Time'])
    sveto = u'Sveto: %s' % (data[direction]['ImatSvet']['Time'])
    vaalimaa = u'Vaalimaa: %s' % (data[direction]['VaalTorf']['Time'])

    if direction == 'ToRussia':
        return u'Venäjälle: %s, %s, %s (%s)' % (nuijamaa, sveto, vaalimaa, updateTime.strftime('%H:%M'))
    return u'Suomeen: %s, %s, %s (%s)' % (nuijamaa, sveto, vaalimaa, updateTime.strftime('%H:%M'))


def command_raja(bot, user, channel, args):
    data = get_data()
    bot.say(channel, make_string(data, 'ToRussia'))
    bot.say(channel, make_string(data, 'ToFinland'))
