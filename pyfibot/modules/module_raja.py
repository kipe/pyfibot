# -*- encoding: utf-8 -*-
import requests
import json
from datetime import datetime, timedelta
import re

rg = re.compile('(\\d+).*?(\\d+).*?(\\d+)', re.IGNORECASE | re.DOTALL)


def get_data():
    try:
        r = requests.get('http://granitsa-online.com/Pages/Splash.aspx', cookies={'CurCulNam': 'en-EN'})
        if r.status_code == 200:
            data = r.text.split("'Cars': ")[1].split("'Trucks': {")[0].replace('\t', '').replace('\n', '').replace('\r', '').replace('\'', '"').rstrip(',')
            return json.loads(data)
    except:
        return


def make_string(data, to_russia):
    def get_updatetime(value):
        updatetime = datetime.now() + timedelta(days=2)
        for k, v in value.iteritems():
            up = datetime.strptime(v['Update'], 'Update time: %m/%d/%Y at %I:%M:%S %p')
            up = up.replace(hour=up.hour - 1)
            if up < updatetime:
                updatetime = up
        return updatetime

    def get_wait(value):
        m = rg.search(value)
        hours = int(m.group(2))
        minutes = int(m.group(3))

        if hours > 0:
            return '%i hours, %i minutes' % (hours, minutes)
        return '%i minutes' % (minutes)

    updatetime = get_updatetime(data)
    nuijamaa = u'Nuijamaa: %s' % (get_wait(data['NuijBrus']['Time']))
    sveto = u'Sveto: %s' % (get_wait(data['ImatSvet']['Time']))
    vaalimaa = u'Vaalimaa: %s' % (get_wait(data['VaalTorf']['Time']))

    if to_russia:
        return u'Venäjälle: %s, %s, %s (%s)' % (nuijamaa, sveto, vaalimaa, updatetime.strftime('%H:%M'))
    return u'  Suomeen: %s, %s, %s (%s)' % (nuijamaa, sveto, vaalimaa, updatetime.strftime('%H:%M'))


def command_raja(bot, user, channel, args):
    data = get_data()
    bot.say(channel, make_string(data['ToRussia'], True))
    bot.say(channel, make_string(data['ToFinland'], False))
