from __future__ import unicode_literals, print_function, division
import pygeoip
import os.path
import sys
import socket

# http://dev.maxmind.com/geoip/legacy/geolite/
DATAFILE = os.path.join(sys.path[0], "GeoIP.dat")

# STANDARD = reload from disk
# MEMORY_CACHE = load to memory
# MMAP_CACHE = memory using mmap
gi4 = pygeoip.GeoIP(DATAFILE, pygeoip.MEMORY_CACHE)


def command_geoip(bot, user, channel, args):
    """Determine the user's country based on host"""
    if not args:
        return bot.say(channel, 'usage: .geoip HOST')

    try:
        country = gi4.country_name_by_name(args)
    except socket.gaierror:
        country = None

    if country:
        return bot.say(channel, "%s is in %s" % (args, country))
