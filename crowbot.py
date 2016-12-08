"""A Slack chatbot for observing"""

import argparse
import time
import ephem
import sys
import requests
import yaml
import datetime as dt
from astropy.coordinates import SkyCoord, AltAz, EarthLocation
from sqlalchemy import create_engine, MetaData, Table, \
                       Column, Integer, String, DateTime
from astropy import units as u
from slackclient import SlackClient
from twilio.rest import TwilioRestClient


# Load configuration and schedule
CONFIG = yaml.load(open('CONFIG.yml', 'r'))
SCHED = yaml.load(open(CONFIG['schedule_path'], 'r'))


# Set up log database
engine = create_engine('sqlite:///'+CONFIG['log_db_path'])
metadata = MetaData()
log = Table('chatlog', metadata,
            Column('id', Integer(), primary_key=True),
            Column('userid', String()),
            Column('channelid', String()),
            Column('time', DateTime()),
            Column('message', String()))
metadata.create_all(engine)
conn = engine.connect()

# Set up Slack and Twilio clients
SC = SlackClient(CONFIG['slack_info']['crowbot_api'])
AT_BOT = '<@{}>'.format(CONFIG['slack_info']['bot_id'])
GROUP = CONFIG['slack_info']['group_channel_id']
TC = TwilioRestClient(CONFIG['twilio_info']['account_sid'], CONFIG['twilio_info']['auth_token'])

# Get information about the telescope location from the configuration file
TELLOC = EarthLocation(lat=CONFIG['telescope_info']['lat']*u.deg,
                       lon=CONFIG['telescope_info']['lon']*u.deg,
                       height=CONFIG['telescope_info']['height']*u.m)
TEL = ephem.Observer()
TEL.lat = str(TELLOC.latitude.value)
TEL.lon = str(TELLOC.longitude.value)
SUN = ephem.Sun()
MOON = ephem.Moon()
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

# Set kill command that puts crow away nicely
KILL_CMD = CONFIG['kill_cmd']


def respond(command, channel):
    """
    Handle commands.
    """
    func = not_implemented
    print(command)
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
                elif KILL_CMD in output['text']:
                    return KILL_CMD, output['channel']
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
        star['airmass'] = altaz.secz
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


def send_sos():
    """
    Send an emergency text+email to contact person
    """
    TC.messages.create(to=CONFIG['sos_num'],
                       from_=CONFIG['twilio_info']['from_num'],
                       body=CONFIG['sos_msg'])
    return 'SOS text message sent to '+str(CONFIG['twilio_info']['sos_num'])


def put_self_away(channel, logfile):
    """
    Write log to a text file, post the location of the log file, and say goodbye
    when kill crow command is given.
    """
    results = conn.execute('select * from chatlog')
    with open(logfile, 'w') as f:
        f.write(','.join(k for k in results.keys())+'\n')
        for r in results:
            f.write(','.join(str(v) for v in r)+'\n')
    message = 'Chat logged to '+logfile+'\nGoodbye!'
    SC.api_call('chat.postMessage', as_user=True,
                channel=channel, text=message)


def convert_sun_times(sched=SCHED):
    """
    Convert time before/after sunset in schedule config file into UTC time.
    """
    now = dt.datetime.utcnow()
    TEL.date = now
    sunset = TEL.next_setting(SUN).datetime()
    sunrise = TEL.next_rising(SUN).datetime()
    new_sched = {}
    for time, message in sched.items():
        if 'SS+' in time:
            td = dt.timedelta(hours=int(time[3:5]), minutes=int(time[6:]))
            time = (sunset+td).strftime('%H:%M')
        elif 'SS-' in time:
            td = dt.timedelta(hours=int(time[3:5]), minutes=int(time[6:]))
            time = (sunset-td).strftime('%H:%M')
        elif 'SR+' in time:
            td = dt.timedelta(hours=int(time[3:5]), minutes=int(time[6:]))
            time = (sunrise+td).strftime('%H:%M')
        elif 'SR-' in time:
            td = dt.timedelta(hours=int(time[3:5]), minutes=int(time[6:]))
            time = (sunrise-td).strftime('%H:%M')
        new_sched[time] = message
    return new_sched


def moon_info():
    now = dt.datetime.utcnow()
    TEL.date = now
    MOON.compute(TEL)
    return ('Current moon position: \n'
            'RA: {!s} \n'
            'Dec: {!s} \n'
            'Current moon illumination: {:.1f}%').format(MOON.ra,
                                                         MOON.dec,
                                                         MOON.phase)


if __name__ == '__main__':
    READ_WEBSOCKET_DELAY = 1
    CHECK_SCHED_DELAY = 60
    check_sched_ind = 0
    SCHED = convert_sun_times(SCHED)
    MATCH = {'time': utc_time,
             'now': utc_time,
             'std': get_standard,
             'standard': get_standard,
             'sun': sun_info,
             'sunset': sun_info,
             'sunrise': sun_info,
             'weather': weather_info,
             'moon': moon_info,
             CONFIG['sos_cmd'].lower(): send_sos}
    ARGMATCH = {'airmass': [get_standard, 'near_secz'],
                'secz': [get_standard, 'near_secz']}
    if SC.rtm_connect():
        parser = argparse.ArgumentParser(description="A Slack chatbot for observing")
        parser.add_argument('--log', '-l', type=str,
                            default=dt.datetime.utcnow().strftime('log_%y_%j_crow_%H%M.txt'),
                            help='Path to chatlog file (default ./log_YY_DDD_crow_HHMM.txt)')
        parser.add_argument('--verbose', '-v', action='store_true',
                            help='Print some status messages to the console')
        args = parser.parse_args()
        if args.verbose:
            print('crowbot connected and running!')
            print('logfile: ' + args.log)
        while True:
            if check_sched_ind % CHECK_SCHED_DELAY == 0:
                now = dt.datetime.now().strftime('%H:%M')
                if now in SCHED.keys():
                    SC.api_call('chat.postMessage', as_user=True,
                                channel=GROUP, text=SCHED[now])
            cmd, chan = parse_slack_output(SC.rtm_read())
            if cmd == KILL_CMD and chan:
                put_self_away(chan, args.log)
                break
            if cmd and chan:
                respond(cmd, chan)
            time.sleep(READ_WEBSOCKET_DELAY)
            check_sched_ind += 1
        if args.verbose:
            print('crow shut down nicely')
    else:
        print("Connection failed. Check the Slack API token, and Bot ID.")
