"""Command line script to have crow send messages to the group channel"""

import sys
import yaml
from slackclient import SlackClient

CONFIG = yaml.load(open(CONFIG.yml, 'r'))
SC = SlackClient(CONFIG['slack_info']['crowbot_api'])
CHANNEL = CONFIG['slack_info']['group_channel_id']
message = str(sys.argv[1])
SC.api_call('chat.postMessage', as_user=True,
            channel=CHANNEL, text=message)
