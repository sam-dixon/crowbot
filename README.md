# Crowbot

Crowbot is a configurable and extensible Slack chatbot for astronomical observing.

## Included features:

* Tells the time until sunset and sunrise (`hey @crowbot when's sunset?`)
* Tells the position and illumination of the moon (`@crowbot how bright is the moon?`)
* Suggests some standard stars at a given airmass (`@crowbot what standard should I use at airmass 1.3?`)
* Looks up the weather (`@crowbot how's the weather?`)
* Sends scheduled messages to remind observers of what they should be doing
* Logs all of the chat messages it can see to an sqlite3 database
* If a specified kill command is given, crowbot will dump the chat logs to a text file and log off
* Sends SOS text messages to a specified contact person if something goes wrong

You can also easily modify or create new functionality by editing `responses.py`.

## Getting started

### Setting up a bot user

### Editing `CONFIG.yml`

### Setting up the schedule

## Adding features