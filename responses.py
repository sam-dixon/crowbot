""" Response functions and configuration for crowbot """

import ephem
import requests
import yaml
import datetime as dt
from astropy.coordinates import SkyCoord, AltAz, EarthLocation
from astropy import units as u
from twilio.rest import TwilioRestClient


# Load configuration file
CONFIG = yaml.load(open('CONFIG.yml', 'r'))

# Set up Twilio client for SOS text messages
try:
    TC = TwilioRestClient(CONFIG['twilio_info']['account_sid'],
                          CONFIG['twilio_info']['auth_token'])
    USE_TWIL = True
except KeyError:
    USE_TWIL = False

# Load schedule
try:
    SCHED = yaml.load(open('SCHEDULE.yml', 'r'))
except FileNotFoundError:
    SCHED = {}

# Get information about the telescope location from the configuration file
# Use this to create astropy EarthLocation object for calculating airmass
# as well as pyephem observer objects for calculating sun and moon locations
TELLOC = EarthLocation(lat=CONFIG['telescope_info']['lat']*u.deg,
                       lon=CONFIG['telescope_info']['lon']*u.deg,
                       height=CONFIG['telescope_info']['height']*u.m)
TEL = ephem.Observer()
TEL.lat = str(TELLOC.latitude.value)
TEL.lon = str(TELLOC.longitude.value)

# Set up pyephem models for the sun and moon
SUN = ephem.Sun()
MOON = ephem.Moon()

# Parse the list of standard stars
STDS = []
with open(CONFIG['standard_path']) as f:
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


def convert_sched_sun_times(sched):
    """
    Convert time before/after sunset in schedule config file into UTC time.
    """
    now = dt.datetime.utcnow()
    TEL.date = now
    sunset = TEL.next_setting(SUN).datetime()
    sunrise = TEL.next_rising(SUN).datetime()
    new_sched = {}
    if type(sched) == dict:
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

# Response functions defined here ############################################


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
        star['airmass'] = altaz.secz.value
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


def weather_info():
    """
    Looks up weather info for the night.
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
    Send an emergency text to contact person specified in CONFIG.
    """
    if USE_TWIL:
        TC.messages.create(to=CONFIG['sos_num'],
                           from_=CONFIG['twilio_info']['from_num'],
                           body=CONFIG['sos_msg'])
        return 'SOS text message sent to '+str(CONFIG['twilio_info']['sos_num'])
    else:
        return not_implemented()

# Define matching dictionaries ################################################


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

# Etc... ######################################################################

SCHED = convert_sched_sun_times(SCHED)
