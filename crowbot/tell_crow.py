"""Command line script to have crow send messages to the group channel"""

import os
import sys
import yaml
from slackclient import SlackClient

WORKDIR = os.path.dirname(__file__)
CONFIG = yaml.load(open(os.path.join(WORKDIR, 'CONFIG.yml'), 'r'))
SC = SlackClient(CONFIG['slack_info']['crowbot_api'])
GROUP = [c['id'] for c in SC.api_call('channels.list')['channels']
         if c['name'] == CONFIG['slack_info']['channel_name']][0]

def main():
    message = str(sys.argv[1])
    SC.api_call('chat.postMessage', as_user=True,
                channel=GROUP, text=message)

if __name__ == '__main__':
    main()
