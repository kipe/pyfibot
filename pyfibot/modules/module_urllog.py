# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division
import sqlite3
import datetime
import os
from modules import module_urltitle


def init(botref):
    global bot
    bot = botref
    bot.config = bot.config.get("module_urltitle", {})
    module_urltitle.init(bot)


def handle_url(bot, user, channel, url, msg):
    ''' Logs urls seen in channels to 'databases/urllog.db' '''
    n = datetime.datetime.now()
    db = os.path.join('databases', 'urllog.db')
    # check if the database exists
    create_db = not os.path.exists(db)
    conn = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # if database doesn't exist, create table
    if create_db:
        sql = ''' CREATE TABLE urls (
            url TEXT UNIQUE PRIMARY KEY,
            title TEXT,
            users VARCHAR(255),
            channels TEXT,
            times_seen INTEGER,
            first_seen timestamp,
            last_seen timestamp
            );'''
        c.execute(sql)

    # check if the url already exists in database
    sql = 'SELECT * FROM urls WHERE url = ? LIMIT 1;'
    c.execute(sql, (url, ))
    row = c.fetchone()
    # if the url already exists in database
    if row:
        # get list of users who said it
        users = row[str('users')].split(',')
        # add current user to users, if not already in it
        if user not in users:
            users.append(user)
        # filter empty strings from list, remove duplicates and join the list to string separated by commas
        users = ','.join(list(set([u for u in filter(None, users)])))

        # get list of channels where it's been
        channels = row[str('channels')].split(',')
        # add current channel to channels, if not already in it
        if channel not in channels:
            channels.append(channel)
        # filter empty strings from list, remove duplicates and join the list to string separated by commas
        channels = ','.join(list(set([ch for ch in filter(None, channels)])))

        # increase the times seen
        times_seen = row[str('times_seen')] + 1

        # update the row, set users, channels, times_seen and last_seen
        sql = 'UPDATE urls SET users = ?, channels = ?, times_seen = ?, last_seen = ? WHERE url = ? LIMIT 1;'
        c.execute(sql, (users, channels, times_seen, n, url))
        # close database connection
        c.close()
        conn.commit()
        conn.close()
        return

    # try to fetch the title via module_urltitle
    try:
        title = module_urltitle.handle_url(bot, user, channel, url, msg, say=False)
    except:
        title = ''

    # title must always exists, default to ''
    if not title:
        title = ''

    # insert data to table
    sql = 'INSERT INTO urls (url, title, users, channels, times_seen, first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?);'
    c.execute(sql, (url, title, user, channel, 1, n, n))
    # close database connection
    c.close()
    conn.commit()
    conn.close()
