# discord-audio-pipe with spotify


Simple program to send stereo audio (microphone, stereo mix, virtual audio cable, etc) into a discord bot.

This fork adds Spotify functionality, to allow the bot to show what is currently playing on a user's Spotify account.

You can download the latest release [**here**](https://github.com/jjwfisher/discord-audio-pipe/releases)
- If you are using the source code, it is recommended to create a venv (using conda, or similar), install the dependencies either manually or (preferred) using environment.yml when creating the venv with conda, and start using `main.pyw`
- The `.exe` does not require python or dependencies

## Setting up a Bot account
1. Follow the steps [**here**](https://docs.pycord.dev/en/master/discord.html) to setup and invite a discord bot
2. To link the program to your bot, create a file ``token.txt`` in the same directory as the `.exe` / `main.pyw` and save the bot token inside

## Setting up Spotify Functions
1. Go to the [**Spotify Developer Dashboard**](https://developer.spotify.com/dashboard), logging in with your existing spotify account if not already.
2. On your dashboard, click "Create App"
3. Put anything you like into all the fields, except for `"Redirect URL"`. This should be `http://localhost:xxxx`, where `xxxx` is a given port. (Shouldn't matter what you choose, I used 8080).
4. In the Spotify Developer Dashboard, click "Settings", then the "Basic Information" tab.
5. When starting DAP, it will ask you for your Spotify API details. Enter your client ID, then click _"View Client Secret"_, and enter this. Finally enter the redirect url you have chosen.
6. When a browser window opens, login in with your Spotify account (if needed), and allow acccess to your application.
7. You should be done! In the future a browser window will open and close itself temporarily to log you in to the Spotify API, or if the .cache file is deleted, or not found.

## Spotify Usage
- To create a "Now Playing" message, message `?np` to any channel the bot has access to.
    - The bot will automatically clean up (delete) your message, and any previous messages it has sent that session. The bot requires the `Manage Messages` permission in Discord to do this. **It also requires the "Read Messages" intent, which you can give in your discord developer settings.**
- The bot will update the latest "Now Playing" message every 5 seconds, and will also update the bot's status.
- If nothing is playing/Spotify is not open, a special embed message will appear noting this.

## Dependencies
Requires Python 3.8+. Install dependencies by running `pip3 install -r requirements.txt`

In some cases PortAudio and xcb libraries may be missing on linux. On Ubuntu they can be installed with
```
    $ sudo apt-get install libportaudio2
    $ sudo apt-get install libxcb-xinerama0
```
macOS requires PortAudio and Opus libraries
```
    $ brew install portaudio --HEAD
    $ brew install opus
```

## CLI
Running the `.exe` / `main.pyw` without any arguments will start the graphical interface. Alternatively, discord-audio-pipe can be run from the command line and contains some tools to query system audio devices and accessible channels.
```
usage: main.pyw [-h] [-t TOKEN] [-v] [-c CHANNEL] [-d DEVICE] [-D] [-C]

Discord Audio Pipe

optional arguments:
  -h, --help            show this help message and exit
  -t TOKEN, --token TOKEN
                        The token for the bot
  -v, --verbose         Enable verbose logging

Command Line Mode:
  -c CHANNEL, --channel CHANNEL
                        The channel to connect to as an id
  -d DEVICE, --device DEVICE
                        The device to listen from as an index

Queries:
  -D, --devices         Query compatible audio devices
  -C, --channels        Query servers and channels (requires token)
```
