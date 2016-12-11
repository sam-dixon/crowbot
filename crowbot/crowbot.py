"""A Slack chatbot for observing"""

import os
import argparse
import time
import datetime as dt
import yaml
from sqlalchemy import create_engine, MetaData, Table, \
                       Column, Integer, String, DateTime
from slackclient import SlackClient
import responses

WORKDIR = os.path.dirname(__file__)

# Load configuration
CONFIG = yaml.load(open(os.path.join(WORKDIR, 'CONFIG.yml'), 'r'))

# Set up log database
ENG = create_engine('sqlite:///'+CONFIG['log_db_path'])
MD = MetaData()
LOG = Table('chatlog', MD,
            Column('id', Integer(), primary_key=True),
            Column('userid', String()),
            Column('channelid', String()),
            Column('time', DateTime()),
            Column('message', String()))
MD.create_all(ENG)
CONN = ENG.connect()

# Where the save the text version of the log
LOGDIR = CONFIG['log_txt_dir']
if not os.path.exists(LOGDIR):
    os.makedirs(LOGDIR)
LOGNAME = dt.datetime.utcnow().strftime('log_%y_%j_crow_%H%M.txt')
LOGPATH = os.path.join(LOGDIR, LOGNAME)

# Set up Slack client
SC = SlackClient(CONFIG['slack_info']['crowbot_api'])
BOTID = [u['id'] for u in SC.api_call('users.list')['members']
         if u['name'] == CONFIG['slack_info']['bot_name']][0]
GROUP = [c['id'] for c in SC.api_call('channels.list')['channels']
         if c['name'] == CONFIG['slack_info']['channel_name']][0]
AT_BOT = '<@{}>'.format(BOTID)

# Set kill command that puts crow away nicely
KILL_CMD = CONFIG['kill_cmd']

# Set match words and argument match dictionary
MATCH = responses.MATCH
ARGMATCH = responses.ARGMATCH

# Load schedule
SCHED = responses.SCHED

def respond(command, channel):
    """
    Handle commands.
    """
    func = responses.not_implemented
    for k in MATCH.keys():
        if k in command:
            func = MATCH[k]
    for k in ARGMATCH.keys():
        kwargs = {}
        if k in command:
            func, keyw = ARGMATCH[k]
            kwargs[keyw] = command.split(k)[1].split()[0]
    response = func(**kwargs)
    SC.api_call('chat.postMessage', as_user=True,
                channel=channel, text=response)
    return response


def parse_slack_output(slack_rtm_output):
    """
    Collects messages directed at the bot and logs all messages
    seen by the bot to the database.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and output['type'] == 'message':
                ins = LOG.insert()
                CONN.execute(ins,
                             user=output['user'],
                             channel=output['channel'],
                             time=dt.datetime.utcnow(),
                             message=output['text'])
                if AT_BOT in output['text']:
                    command = output['text'].split(AT_BOT)[1].strip().lower()
                    command = command.replace('?', '')
                    return command, output['channel']
                elif KILL_CMD in output['text']:
                    return KILL_CMD, output['channel']
    return None, None


def put_self_away(channel, logfile):
    """
    Write log to a text file, post the location of the log file, and say
    goodbye, all after the kill command is given.
    """
    results = CONN.execute('select * from chatlog')
    with open(logfile, 'w') as log:
        log.write(','.join(k for k in results.keys())+'\n')
        for result in results:
            log.write(','.join(str(v) for v in result)+'\n')
    message = 'Chat logged to '+logfile+'\nGoodbye!'
    SC.api_call('chat.postMessage', as_user=True,
                channel=channel, text=message)
    return message


if __name__ == '__main__':
    READ_WEBSOCKET_DELAY = 1

    # Parse command line arguments
    PARSER = argparse.ArgumentParser(description="An observing chatbot")
    PARSER.add_argument('--verbose', '-v', action='store_true',
                        help='Print some status messages to the console')
    ARGS = PARSER.parse_args()

    # Check connection
    if SC.rtm_connect():
        if ARGS.verbose:
            print('crowbot connected and running!')
        # Main loop
        while True:
            NOW = dt.datetime.now().strftime('%H:%M')
            # Check if current time is listed in the schedule
            if NOW in SCHED.keys():
                SC.api_call('chat.postMessage', as_user=True,
                            channel=GROUP, text=SCHED[NOW])
            # Then listen for commands
            CMD, CHAN = parse_slack_output(SC.rtm_read())
            # If kill command is given, put self away and end loop
            if CMD == KILL_CMD and CHAN:
                put_self_away(CHAN, LOGPATH)
                break
            # Otherwise, respond to command
            if CMD and CHAN:
                respond(CMD, CHAN)
            # Wait some time
            time.sleep(READ_WEBSOCKET_DELAY)
        if ARGS.verbose:
            print('crow shut down nicely')
    else:
        print("Connection failed. Check the Slack API token, and Bot ID.")
