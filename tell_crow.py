"""Command line script to have crow send messages to the group channel"""

import sys
from slackclient import SlackClient
from keys import CROWBOT_API, GROUP_CHANNEL_ID

SC = SlackClient(CROWBOT_API)
CHANNEL = GROUP_CHANNEL_ID
message = str(sys.argv[1])
SC.api_call('chat.postMessage', as_user=True,
            channel=CHANNEL, text=message)
