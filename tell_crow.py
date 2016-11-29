import sys
from slackclient import SlackClient
from keys import BOT_ID, CROWBOT_API

SC = SlackClient(CROWBOT_API)
CHANNEL = 'C0VHU6ES3'
message = sys.argv[1]
SC.api_call('chat.postMessage', as_user=True,
                channel=CHANNEL, text=message)