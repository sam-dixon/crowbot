from slackclient import SlackClient
import datetime as dt
import time
from keys import *


slack_client = SlackClient(CROWBOT_API)
AT_BOT = '<@{}>'.format(BOT_ID)

def respond(command, channel):
    """
    Handle commands.
    """
    func = not_implemented
    MATCH = {}
    for k in MATCH.keys():
        if k in command:
            func = MATCH[k]
    response = func(channel)
    slack_client.api_call('chat.postMessage', as_user=True,
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


if __name__ == '__main__':
    READ_WEBSOCKET_DELAY = 0.5
    if slack_client.rtm_connect():
        print("crowbot connected and running!")
        while True:
            command, channel = parse_slack_output(slack_client.rtm_read())
            if command and channel:
                respond(command, channel)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Check the Internet connect, Slack API token, and Bot ID.")