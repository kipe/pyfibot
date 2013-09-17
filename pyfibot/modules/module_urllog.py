# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division
import sqlite3
import datetime
import os
from modules import module_urltitle


db = os.path.join('databases', 'urllog.db')


def init(bot):
    module_urltitle.init(bot)


def __get_conn():
    conn = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    return conn, c


def handle_url(bot, user, channel, url, msg):
    ''' Logs urls seen in channels to 'databases/urllog.db' '''
    global db
    n = datetime.datetime.now()
    # check if the database exists
    create_db = not os.path.exists(db)
    conn, c = __get_conn()

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


def command_find_url(bot, user, channel, args):
    global db
    args = args.strip()
    if not args:
        return bot.say(channel, 'I need search parameters.')

    search_str = args.replace('*', '%%')

    if not os.path.exists(db):
        return bot.say(channel, 'I haven\'t logged any urls yet.')

    sql = 'SELECT * FROM urls WHERE channels LIKE ? AND (url LIKE ? OR title LIKE ?);'

    conn, c = __get_conn()
    c.execute(sql, ('%%%s%%' % channel, search_str, search_str))
    rows = c.fetchall()
    c.close()
    conn.close()

    if not rows:
        return bot.say(channel, 'No search results.')

    if len(rows) > 1:
        return bot.say(channel, 'Found multiple results, please redefine your search string.')

    row = rows[0]

    return bot.say(channel, '%s <%s>' % (row[str('title')], row[str('url')]))
