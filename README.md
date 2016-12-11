# Crowbot

Crowbot is a configurable and extensible Slack chatbot for astronomical observing.

![Crowbot in action](https://github.com/sam-dixon/crowbot/raw/master/cap.gif)

## Included features:

* Tells the time until sunset and sunrise (`hey @crowbot when's sunset?`)
* Tells the position and illumination of the moon (`@crowbot how bright is the moon?`)
* Suggests some standard stars at a given airmass (`@crowbot what standard should I use at airmass 1.3?`)
* Looks up the weather (`@crowbot how's the weather?`)
* Sends scheduled messages to remind observers of what they should be doing
* Logs all of the chat messages it can see to an sqlite3 database
* If a specified kill command is given, Crowbot will dump the chat logs to a text file and log off
* Sends SOS text messages to a specified contact person if something goes wrong
* `tell_crow.py` allows you to speak through Crowbot from the command line. You can integrate this into telescope control scripts to post status updates or error messages to the group channel

You can also easily modify existing features or create new functionality by editing `responses.py`.

## Getting started

First, install the package and all dependencies with
```
python setup.py install
```

### Setting up your Slack environment
Crowbot uses the Slack API to communicate. Follow the instructions [here](https://api.slack.com/bot-users) to set up a new bot user integration. Make note of the bot access token that gets generated.

### Setting up Twilio (optional)
If you want Crowbot to be able to send emergency text messages, you'll need an account with [Twilio](https://www.twilio.com/). Signing up for an account gives you an account ID and an authorization token, as well as a phone number that will be used to send these text messages.

If you don't want to deal with this, you can remove the `twilio_info` block from the CONFIG.yml file.

### Editing `CONFIG.yml`
Make a copy of the `config/CONFIG_example.yml` file and save it as `config/CONFIG.yml`. This is where you can enter all of the information Crowbot needs to work. The example file explains what each item does.

### Setting up the schedule
Crowbot can send reminder messages to the group channel. Like the `CONFIG` file, just make a copy of `config/SCHEDULE_example.yml` and save it as `config/SCHEDULE.yml`. You can add entries as (time, message) pairs. 

You can also set times that reference sunrise and sunset. For example, to have a message that goes out 15 minutes before sunset, set the time as `'SS-00:15'`. For a message that goes out an hour after sunrise, set the time to be `'SR+01:00'`.

If you don't want to use scheduled messages, either leave `SCHEDULE.yml` empty, or don't include it in the directory at all.

### Using a different standard star list
An example list of standard stars is include under `standards.txt`. You can use your own list and add the path to that list in the config file.

### Run Crowbot
Now that the hard work is done, run Crowbot with
```
python crowbot/crowbot.py [-v]
```
The `-v` flag runs `crowbot.py` in verbose mode, so some status messages are printed to the console.

Note: Crowbot only responds when @ mentioned, even in a direct message.

## Adding features
`crowbot.py` is responsible for handling messages from Slack and logging them to the database. The way Crowbot responds is all determined in `responses.py`. That script is structured in three main sections.

* Object constructions: defining objects that are used in some of the response calculations (e.g. astropy `EarthLocation` objects used for calculating airmass or pyephem objects for determining the positions of the sun and moon)
* Response definitions: Each function defined here is a different response feature. The return value of each function should be the string that gets posted to whatever channel the question came from.
* Match mapping: The `MATCH` dictionary maps the match word to the response function. The keys are all strings, and the values are functions defined in `responses.py`. If a response function takes arguments, include the argument match word as a key in `ARGMATCH`. The value corresponding to that key is a list, with the first element being the function that you wish to call, and the remaining being the keywords of the arguments (as strings).

To create a new feature, then, just define a new function and add the match words and keyword argument match words to the `MATCH` and `ARGMATCH` dictionaries.

## `tell_crow`
`tell_crow.py` allows you to speak through Crowbot from the command line. Just run
```
python crowbot/tell_crow.py "Your message here"
```

## Stopping Crowbot
If you want Crowbot to put itself away nicely, you can just send the kill command you entered in `CONFIG.yml` as a message anywhere Crowbot can see it (i.e. the group channel you configured or as a direct message). There's no need to @ mention in this case.

Crowbot will dump the log to a text file in the configured text log directory.