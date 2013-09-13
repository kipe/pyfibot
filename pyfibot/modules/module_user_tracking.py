# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division
import sqlite3
import os
from datetime import datetime


class UserSQL:
    def __init__(self, bot):
        self.db_dir = os.path.join('databases', bot.network.alias)
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)

    def _get_conn(self, channel, user=None):
        '''
        Create connection to database (create it if doesn't exist)
        Also creates user, if arg is present (and user doesn't exist in db).
        '''
        channel_db = os.path.join(self.db_dir, channel + '.db')
        create_db = not os.path.exists(channel_db)
        self.conn = sqlite3.connect(channel_db, detect_types=sqlite3.PARSE_DECLTYPES)
        self.c = self.conn.cursor()

        if create_db:
            sql = ''' CREATE TABLE users (
                nick VARCHAR(25) UNIQUE PRIMARY KEY,
                ident VARCHAR(25),
                host VARCHAR(255),
                last_message TEXT,
                last_spoke timestamp,
                last_event VARCHAR(25),
                last_seen timestamp,
                autoop BOOLEAN,
                autovoice BOOLEAN,
                alternative_nicks TEXT
                );'''
            self.c.execute(sql)

        # if user is specified, create it (or if exists already, ignore)
        if user is not None:
            nick = getNick(user)
            ident = getIdent(user)
            host = getHost(user)

            sql = 'INSERT OR IGNORE INTO users (nick, ident, host, last_seen, autoop, autovoice, alternative_nicks) VALUES (?, ?, ?, ?, ?, ?, ?);'
            data = (nick, ident, host, datetime.now(), False, False, '')
            self.c.execute(sql, data)

    def _close_conn(self):
        '''Close connection cleanly.'''
        self.c.close()
        self.conn.commit()
        self.conn.close()

    def _get_alternative_nicks(self, user):
        '''Fetches users alternative nicks from database. Returns list of nicks.'''
        nick = getNick(user)
        ident = getIdent(user)
        host = getHost(user)

        sql = 'SELECT alternative_nicks FROM users WHERE nick = ? AND ident = ? AND host = ? LIMIT 1;'
        data = (nick, ident, host)
        self.c.execute(sql, data)
        row = self.c.fetchone()
        if row:
            return filter(None, row[0].split(','))
        return []

    def update_user(self, user, channel, event, message=None, spoke=False):
        '''Updates user data to database.'''
        nick = getNick(user)
        ident = getIdent(user)
        host = getHost(user)
        now = datetime.now()

        # create connection and create user, if doesn't already exist
        self._get_conn(channel, user)

        # update last event and last seen
        sql = 'UPDATE users SET last_event = ?, last_seen = ? WHERE nick = ? AND ident = ? AND host = ? LIMIT 1;'
        data = (event, now, nick, ident, host)
        self.c.execute(sql, data)

        # if message is specified, update it
        if message:
            sql = 'UPDATE users SET last_message = ? WHERE nick = ? AND ident = ? AND host = ? LIMIT 1;'
            data = (message, nick, ident, host)
            self.c.execute(sql, data)

        # if the user spoke, update last_spoke
        if spoke:
            sql = 'UPDATE users SET last_spoke = ? WHERE nick = ? AND ident = ? AND host = ? LIMIT 1;'
            data = (now, nick, ident, host)
            self.c.execute(sql, data)

        self._close_conn()

    def kicked(self, kickee, channel, kicker, message):
        '''Handle user being kicked.'''
        # TODO: try and get user instead of nick
        # Seems like needs a working whois, as botcore.userKicked receives only nick from kickee
        # Kicker however is an user -object...
        now = datetime.now()
        # can't create user
        self._get_conn(channel)
        event = 'kicked by %s [%s]' % (kicker, message)
        # for now, we need to update based on nick
        sql = 'UPDATE users SET last_event = ?, last_seen = ? WHERE nick = ? LIMIT 1;'
        data = (event, now, kickee)
        self.c.execute(sql, data)
        self._close_conn()

    def nick_change(self, user, newnick):
        '''Handle user nick change.'''
        nick = getNick(user)
        ident = getIdent(user)
        host = getHost(user)

        now = datetime.now()
        # loop through the networks databases and change nick to every db
        for f in os.listdir(self.db_dir):
            if f.endswith('.db'):
                # DON'T create user here, we don't want it on every database of network
                self._get_conn(f.strip('.db'))
                # Get users alternative nicks
                alternative_nicks = self._get_alternative_nicks(user)
                # if new nick is already in alternative nicks, remove it
                if newnick in alternative_nicks:
                    alternative_nicks.remove(newnick)
                # add old nick to alternative nicks
                alternative_nicks.append(nick)

                sql = 'UPDATE users SET nick = ?, last_event = ?, last_seen = ?, alternative_nicks = ? WHERE nick = ? AND ident = ? AND host = ? LIMIT 1;'
                data = (newnick, 'nick_change', now, ','.join(alternative_nicks), nick, ident, host)
                self.c.execute(sql, data)
                self._close_conn()

    def user_quit(self, user, message):
        '''Handle user quitting.'''
        nick = getNick(user)
        ident = getIdent(user)
        host = getHost(user)

        now = datetime.now()
        # loop through the networks databases and change nick to every db
        for f in os.listdir(self.db_dir):
            if f.endswith('.db'):
                # DON'T create user here, we don't want it on every database of network
                self._get_conn(f.strip('.db'))
                sql = 'UPDATE users SET last_message = ?, last_event = ?, last_seen = ? WHERE nick = ? AND ident = ? AND host = ? LIMIT 1;'
                data = (message, 'quit', now, nick, ident, host)
                self.c.execute(sql, data)
                self._close_conn()

    def find_nick(self, bot, nick, channel):
        '''Finds row by nick from database.'''
        alternative = False

        self._get_conn(channel)
        # search nick
        sql = 'SELECT * FROM users WHERE nick = ? LIMIT 1;'
        data = (nick,)
        self.c.execute(sql, data)
        row = self.c.fetchone()

        if not row:
            alternative = True
            sql = 'SELECT * FROM users WHERE alternative_nicks LIKE ? LIMIT 1;'
            data = ('%%%s%%' % nick,)
            self.c.execute(sql, data)
            row = self.c.fetchone()
            if row:
                alternative_nicks = filter(None, row[9].split(','))
                if nick not in alternative_nicks:
                    row = None

        self._close_conn()
        return row, alternative


def handle_privmsg(bot, user, channel, message):
    # no need to log private messages...
    if user == channel:
        return

    s = UserSQL(bot)
    s.update_user(user, channel, 'message', message, True)


def handle_userJoined(bot, user, channel):
    s = UserSQL(bot)
    s.update_user(user, channel, 'join')


def handle_userLeft(bot, user, channel, message):
    s = UserSQL(bot)
    if channel is not None:
        s.update_user(user, channel, 'left', message)
    else:
        s.user_quit(user, message)


def handle_userKicked(bot, kickee, channel, kicker, message):
    s = UserSQL(bot)
    s.kicked(kickee, channel, kicker, message)


def handle_userRenamed(bot, user, newnick):
    s = UserSQL(bot)
    s.nick_change(user, newnick)


def command_lastseen(bot, user, channel, args):
    args = args.strip()
    if not args:
        return bot.say(channel, 'Please provide nick to search.')

    s = UserSQL(bot)
    row, alternative = s.find_nick(bot, args, channel)
    msg = 'I have no idea who %s is. At least I haven\'t seen him/her on %s.' % (args, channel)
    if row:
        msg = '%s!%s@%s was last seen at %s (%s)' % (row[0], row[1], row[2], row[6].strftime('%d.%m.%y %H:%M'), row[5])
    return bot.say(channel, msg)


def command_lastspoke(bot, user, channel, args):
    args = args.strip()
    if not args:
        return bot.say(channel, 'Please provide nick to search.')

    s = UserSQL(bot)
    row, alternative = s.find_nick(bot, args, channel)
    msg = 'I have no idea who %s is. At least I haven\'t seen him/her on %s.' % (args, channel)
    if row:
        msg = '%s!%s@%s last spoke at %s' % (row[0], row[1], row[2], row[4].strftime('%d.%m.%y %H:%M'))
    return bot.say(channel, msg)
