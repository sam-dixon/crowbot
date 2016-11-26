from slackclient import SlackClient
import datetime as dt
import time
from keys import *
from astropy.coordinates import SkyCoord, AltAz, EarthLocation
from astropy import units as u


SC = SlackClient(CROWBOT_API)
AT_BOT = '<@{}>'.format(BOT_ID)
TELLOC = EarthLocation(lat=19.822991067*u.deg, lon=-155.469433536*u.deg, height=4205*u.m)
STDS = []
with open('standards.txt') as f:
    while f.readline():
        l = f.readline().split()
        if len(l) > 0:
            std = {}
            std['name'] = l[0]
            std['coord'] = SkyCoord('{} {} {} {} {} {}'.format(*l[1:7]), unit=(u.hourangle, u.deg))
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
    response = func(channel, **kwargs)
    SC.api_call('chat.postMessage', as_user=True,
                          channel=channel, text=response)


def parse_slack_output(slack_rtm_output):
    """
    Collects messages directed at the bot
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # return text after the @ mention, whitespace removed
                return output['text'].split(AT_BOT)[1].strip().lower(), output['channel']
    return None, None


def not_implemented(channel):
    return "Sorry, I can't do that yet!"


def utc_time(channel):
    now = dt.datetime.utcnow()
    return 'Current UTC time: {}'.format(now)


def get_standard(channel, near_secz=1.0):
    """
    Responds with some good standards to use near a given airmass.
    If no airmass is given, assumes 1.0"""
    now = dt.datetime.utcnow()
    near_secz = float(near_secz)
    for std in STDS:
        std['airmass'] = std['coord'].transform_to(AltAz(obstime=now, location=TELLOC)).secz
    sorted_stds = sorted(STDS, key=lambda k: abs(k['airmass']-near_secz))
    first, second = sorted_stds[:2]
    return ('How about {}, a {} mag {} star at airmass {:0.4}?\n'
            'Or alternatively, {}, a {} mag {} star at airmass {:0.4}?').format(first['name'],
                                                                                first['mag'],
                                                                                first['type'],
                                                                                first['airmass'],
                                                                                second['name'],
                                                                                second['mag'],
                                                                                second['type'],
                                                                                second['airmass'])


if __name__ == '__main__':
    READ_WEBSOCKET_DELAY = 0.5
    MATCH = {'time': utc_time,
         'std': get_standard,
         'standard': get_standard}
    ARGMATCH = {'airmass': [get_standard, 'near_secz'],
                'secz': [get_standard, 'near_secz']}
    if SC.rtm_connect():
        print("crowbot connected and running!")
        while True:
            command, channel = parse_slack_output(SC.rtm_read())
            if command and channel:
                respond(command, channel)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Check the Internet connect, Slack API token, and Bot ID.")