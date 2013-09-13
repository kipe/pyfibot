# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division
import sqlite3
import os
from datetime import datetime
import logging

log = logging.getLogger('user_tracking')


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
        self.conn.row_factory = sqlite3.Row
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
        ''' Close connection cleanly. '''
        self.c.close()
        self.conn.commit()
        self.conn.close()

    def _get_user(self, user):
        ''' Fetches user row from database '''
        selector, data = self._get_user_selector(user)
        sql = 'SELECT * FROM users WHERE %s LIMIT 1;' % selector
        self.c.execute(sql, data)
        return self.c.fetchone()

    def _get_user_selector(self, user):
        '''
        Creates selectors for sql from nickmask, nick etc.
        Used in many situations, normally full mask is available -> nick, ident and host.
        '''
        nick = getNick(user)
        try:
            ident = getIdent(user)
        except:
            ident = None
        try:
            host = getHost(user)
        except:
            host = None

        if ident and host:
            sql = 'nick = ? AND ident = ? AND host = ?'
            data = (nick, ident, host)
        elif ident:
            sql = 'nick = ? AND ident = ?'
            data = (nick, ident)
        else:
            sql = 'nick = ?'
            data = (nick, )
        return sql, data

    def _get_alternative_nicks(self, user):
        ''' Fetches users alternative nicks from database. Returns list of nicks. '''
        selector, data = self._get_user_selector(user)

        sql = 'SELECT alternative_nicks FROM users WHERE %s LIMIT 1;' % (selector)
        self.c.execute(sql, data)
        row = self.c.fetchone()
        if row:
            return filter(None, row[str('alternative_nicks')].split(','))
        return []

    def update_user(self, bot, user, channel, event, message=None, spoke=False):
        ''' Updates user data to database. '''
        selector, selector_data = self._get_user_selector(user)
        now = datetime.now()

        # create connection and create user, if doesn't already exist
        self._get_conn(channel, user)

        # update last event and last seen
        sql = 'UPDATE users SET last_event = ?, last_seen = ? WHERE %s LIMIT 1;' % (selector)
        data = (event, now) + selector_data
        self.c.execute(sql, data)

        # if message is specified, update it
        if message:
            sql = 'UPDATE users SET last_message = ? WHERE %s LIMIT 1;' % (selector)
            data = (message,) + selector_data
            self.c.execute(sql, data)

        # if the user spoke, update last_spoke
        if spoke:
            sql = 'UPDATE users SET last_spoke = ? WHERE %s LIMIT 1;' % (selector)
            data = (now,) + selector_data
            self.c.execute(sql, data)

        if event == 'join':
            sql = 'SELECT autoop, autovoice FROM users WHERE %s LIMIT 1;' % (selector)
            self.c.execute(sql, selector_data)
            row = self.c.fetchone()
            if row[str('autoop')]:
                bot.mode(channel, True, 'o', user=selector_data[0])
                log.info('user %s autoopped on %s' % (user, channel))

        self._close_conn()
        log.debug('user %s updated' % (user))

    def kicked(self, kickee, channel, kicker, message):
        ''' Handle user being kicked. '''
        # TODO: try and get user instead of nick
        # Seems like needs a working whois, as botcore.userKicked receives only nick from kickee
        # Kicker however is an user -object...
        now = datetime.now()
        selector, selector_data = self._get_user_selector(user)
        # can't create user
        self._get_conn(channel)
        event = 'kicked by %s [%s]' % (kicker, message)
        # for now, we need to update based on nick
        sql = 'UPDATE users SET last_event = ?, last_seen = ? WHERE %s LIMIT 1;' % selector
        data = (event, now) + selector_data
        self.c.execute(sql, data)
        self._close_conn()

        log.info('user %s kicked from %s by %s [%s]' % (kickee, channel, kicker, message))

    def nick_change(self, user, newnick):
        ''' Handle user nick change. '''
        selector, selector_data = self._get_user_selector(user)

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

                sql = 'UPDATE users SET nick = ?, last_event = ?, last_seen = ?, alternative_nicks = ? WHERE %s LIMIT 1;' % selector
                data = (newnick, 'nick_change', now, ','.join(alternative_nicks)) + selector_data
                self.c.execute(sql, data)
                self._close_conn()
        log.debug('user %s is now known as %s' % (user, newnick))

    def user_quit(self, user, message):
        ''' Handle user quitting. '''
        selector, selector_data = self._get_user_selector(user)

        now = datetime.now()
        # loop through the networks databases and change nick to every db
        for f in os.listdir(self.db_dir):
            if f.endswith('.db'):
                # DON'T create user here, we don't want it on every database of network
                self._get_conn(f.strip('.db'))
                sql = 'UPDATE users SET last_message = ?, last_event = ?, last_seen = ? WHERE %s LIMIT 1;' % selector
                data = (message, 'quit', now) + selector_data
                self.c.execute(sql, data)
                self._close_conn()
        log.debug('user %s quit [%s]' % (user, message))

    def find_nick(self, bot, nick, channel):
        ''' Finds row by nick from database. '''
        alternative = False

        self._get_conn(channel)
        # search nick
        sql = 'SELECT * FROM users WHERE nick = ? LIMIT 1;'
        data = (nick,)
        self.c.execute(sql, data)
        row = self.c.fetchone()

        # if not found by last one, search by alternative nick
        if not row:
            alternative = True
            sql = 'SELECT * FROM users WHERE alternative_nicks LIKE ? LIMIT 1;'
            data = ('%%%s%%' % nick,)
            self.c.execute(sql, data)
            row = self.c.fetchone()
            if row:
                alternative_nicks = filter(None, row[str('alternative_nicks')].split(','))
                # check that the search term really is in the alternative nick -list, else don't want to give out crap
                if nick not in alternative_nicks:
                    row = None

        self._close_conn()
        return row, alternative

    def set_autoop(self, user, channel, state):
        '''
        Sets auto-op status for user.
        Returns:
            - 0 if can't find the user (or autop-op state already is what we wanted)
            - SQL row of user, if the user was changed.
        '''
        reval = None
        selector, selector_data = self._get_user_selector(user)

        # NOTE: The user-mask might be incomplete, don't want to create user with that info.
        self._get_conn(channel)
        sql = 'UPDATE users SET autoop = ? WHERE autoop = ? AND %s LIMIT 1;' % (selector)
        self.c.execute(sql, (state, not state) + selector_data)
        reval = self.c.rowcount
        # if there was rows affected, fetch the users row
        if reval:
            reval = self._get_user(user)
        self._close_conn()
        return reval


# HANDLERS
def handle_privmsg(bot, user, channel, message):
    # no need to log private messages...
    if user == channel:
        return

    s = UserSQL(bot)
    s.update_user(bot, user, channel, 'message', message, True)


def handle_userJoined(bot, user, channel):
    s = UserSQL(bot)
    s.update_user(bot, user, channel, 'join')


def handle_userLeft(bot, user, channel, message):
    s = UserSQL(bot)
    if channel is not None:
        s.update_user(bot, user, channel, 'left', message)
    else:
        s.user_quit(user, message)


def handle_userKicked(bot, kickee, channel, kicker, message):
    s = UserSQL(bot)
    s.kicked(kickee, channel, kicker, message)


def handle_userRenamed(bot, user, newnick):
    s = UserSQL(bot)
    s.nick_change(user, newnick)


# COMMANDS
def command_lastseen(bot, user, channel, args):
    ''' Search for user, returns when the user was last seen. '''
    args = args.strip()
    if not args:
        return bot.say(channel, 'Please provide nick to search.')

    s = UserSQL(bot)
    row, alternative = s.find_nick(bot, args, channel)
    msg = 'I have no idea who %s is. At least I haven\'t seen him/her on %s.' % (args, channel)
    if row:
        msg = '%s!%s@%s was last seen at %s (%s)' % (
            row[str('nick')], row[str('ident')], row[str('host')],
            row[str('last_seen')].strftime('%d.%m.%y %H:%M'), row[str('last_event')])
    return bot.say(channel, msg)


def command_lastspoke(bot, user, channel, args):
    ''' Search for user, returns when the user last spoke. '''
    args = args.strip()
    if not args:
        return bot.say(channel, 'Please provide nick to search.')

    s = UserSQL(bot)
    row, alternative = s.find_nick(bot, args, channel)
    msg = 'I have no idea who %s is. At least I haven\'t seen him/her on %s.' % (args, channel)
    if row:
        msg = '%s!%s@%s last spoke at %s' % (row[str('nick')], row[str('ident')], row[str('host')], row[str('last_spoke')].strftime('%d.%m.%y %H:%M'))
    return bot.say(channel, msg)


def command_set_autoop(bot, user, channel, args):
    ''' Sets autoop for user. '''
    args = args.strip()
    if not isAdmin(user) or not args:
        return

    msg = 'No user found with "%s".' % (args)
    s = UserSQL(bot)
    row = s.set_autoop(args, channel, True)
    if row:
        msg = 'Auto-opping %s!%s@%s on %s.' % (row[str('nick')], row[str('ident')], row[str('host')], channel)
        log.info(msg)
    return bot.say(channel, msg)


def command_remove_autoop(bot, user, channel, args):
    ''' Removes autoop from user. '''
    args = args.strip()
    if not isAdmin(user) or not args:
        return

    msg = 'No user found with "%s" (or not auto-opped).' % (args)
    s = UserSQL(bot)
    row = s.set_autoop(args, channel, False)
    if row:
        msg = 'Removed auto-op from %s!%s@%s on %s.' % (row[str('nick')], row[str('ident')], row[str('host')], channel)
        log.info(msg)
    return bot.say(channel, msg)
