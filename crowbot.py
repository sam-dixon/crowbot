"""An observing chatbot for Slack"""

import time
import ephem
import sys
import requests
import datetime as dt
from astropy.coordinates import SkyCoord, AltAz, EarthLocation
from sqlalchemy import create_engine, MetaData, Table, \
                       Column, Integer, String, DateTime
from astropy import units as u
from slackclient import SlackClient
from keys import BOT_ID, CROWBOT_API


engine = create_engine('sqlite:///log.db')
metadata = MetaData()
log = Table('chatlog', metadata,
            Column('id', Integer(), primary_key=True),
            Column('user', String()),
            Column('channel', String()),
            Column('time', DateTime()),
            Column('message', String()))
metadata.create_all(engine)
conn = engine.connect()

SC = SlackClient(CROWBOT_API)
AT_BOT = '<@{}>'.format(BOT_ID)
TELLOC = EarthLocation(lat=19.822991067*u.deg,
                       lon=-155.469433536*u.deg,
                       height=4205*u.m)
TEL = ephem.Observer()
TEL.lat = str(TELLOC.latitude.value)
TEL.lon = str(TELLOC.longitude.value)
SUN = ephem.Sun()
STDS = []
with open('standards.txt') as f:
    while f.readline():
        l = f.readline().split()
        if len(l) > 0:
            std = {}
            std['name'] = l[0]
            std['coord'] = SkyCoord('{} {} {} {} {} {}'.format(*l[1:7]),
                                    unit=(u.hourangle, u.deg))
            std['mag'] = l[7]
            std['type'] = l[8]
            STDS.append(std)


def respond(command, channel):
    """
    Handle commands.
    """
    func = not_implemented
    for k in MATCH.keys():
        if k in command:
            func = MATCH[k]
    for k in ARGMATCH.keys():
        kwargs = {}
        if k in command:
            func, kw = ARGMATCH[k]
            kwargs[kw] = command.split(k)[1].split()[0]
    response = func(**kwargs)
    SC.api_call('chat.postMessage', as_user=True,
                channel=channel, text=response)


def parse_slack_output(slack_rtm_output):
    """
    Collects messages directed at the bot and logs all messages
    seen by the bot to the database.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and output['type'] == 'message':
                ins = log.insert()
                conn.execute(ins,
                             user=output['user'],
                             channel=output['channel'],
                             time=dt.datetime.utcnow(),
                             message=output['text'])
                if AT_BOT in output['text']:
                    command = output['text'].split(AT_BOT)[1].strip().lower()
                    return command, output['channel']
    return None, None


def not_implemented():
    """
    Responds if functionality not yet implemented
    """
    return "Sorry, I can't do that yet!"


def utc_time():
    """
    Responds with current UTC time
    """
    now = dt.datetime.utcnow()
    return 'Current UTC time: {}'.format(now)


def get_standard(near_secz=1.0):
    """
    Responds with some good standards to use near a given airmass.
    If no airmass is given, assumes 1.0
    """
    now = dt.datetime.utcnow()
    near_secz = float(near_secz)
    for star in STDS:
        altaz = star['coord'].transform_to(AltAz(obstime=now, location=TELLOC))
        std['airmass'] = altaz.secz
    sorted_stds = sorted(STDS, key=lambda k: abs(k['airmass']-near_secz))
    first, second = sorted_stds[:2]
    string = ('How about {}, a {} mag {} star at airmass {:0.4}?\n'
              'Or {}, a {} mag {} star at airmass {:0.4}?')
    return string.format(first['name'],
                         first['mag'],
                         first['type'],
                         first['airmass'],
                         second['name'],
                         second['mag'],
                         second['type'],
                         second['airmass'])


def sun_info():
    """
    Calculates when sunrise/sunset will be
    """
    try:
        now = dt.datetime.utcnow()
        TEL.date = now
        sunset = TEL.next_setting(SUN).datetime()
        to_sunset = ':'.join(str(sunset - now).split(':')[:2])
        TEL.horizon = '-6'
        civil = TEL.next_setting(SUN).datetime()
        TEL.horizon = '-12'
        naut = TEL.next_setting(SUN).datetime()
        TEL.horizon = '-18'
        astro = TEL.next_setting(SUN).datetime()
        TEL.horizon = '0'
        sunrise = TEL.next_rising(SUN).datetime()
        to_sunrise = ':'.join(str(sunrise - now).split(':')[:2])
        response = ('Current UTC time: {:%Y/%m/%d %H:%M}\n'
                    'Sunset: {:%Y/%m/%d %H:%M} (in {})\n'
                    '6 deg. twilight: {:%Y/%m/%d %H:%M}\n'
                    '12 deg. twilight: {:%Y/%m/%d %H:%M}\n'
                    '18 deg. twilight: {:%Y/%m/%d %H:%M}\n\n'
                    'Sunrise: {:%Y/%m/%d %H:%M} (in {})').format(now,
                                                                 sunset,
                                                                 to_sunset,
                                                                 civil,
                                                                 naut,
                                                                 astro,
                                                                 sunrise,
                                                                 to_sunrise)
    except:
        response = 'Whoops! Something went wrong:\n'+str(sys.exc_info())
    return response


def weather_info():
    """
    Looks up weather info for the night
    """
    r = requests.get('http://www.cfht.hawaii.edu/cgi-bin/dl_gemini.csh')
    if r.status_code != 200:
        return ('Something went wrong connecting to the CFHT weather center.\n'
                'See: http://www.cfht.hawaii.edu/ObsInfo/Weather/')
    timestamp, ws, wd, temp, rh, bp = [l.split('#')[0].split('=')[-1].strip()
                                       for l in r.text.split('\n')[1:-1]]
    return ('Weather info accessed from '
            'http://www.cfht.hawaii.edu/cgi-bin/dl_gemini.csh\n'
            '{}\n'
            'Wind speed: {} knots\n'
            'Wind direction: {} deg\n'
            'Temperature: {} deg. C\n'
            'Rel. humidity: {} %\n'
            'Baro. pressure: {} mbar').format(timestamp, ws, wd, temp, rh, bp)


if __name__ == '__main__':
    READ_WEBSOCKET_DELAY = 0.5
    MATCH = {'time': utc_time,
             'now': utc_time,
             'std': get_standard,
             'standard': get_standard,
             'sun': sun_info,
             'sunset': sun_info,
             'sunrise': sun_info,
             'weather': weather_info}
    ARGMATCH = {'airmass': [get_standard, 'near_secz'],
                'secz': [get_standard, 'near_secz']}
    if SC.rtm_connect():
        print("crowbot connected and running!")
        while True:
            cmd, chan = parse_slack_output(SC.rtm_read())
            if cmd and chan:
                respond(cmd, chan)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Check the Slack API token, and Bot ID.")
