import logging

# error logging
error_formatter = logging.Formatter(
    fmt="%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

error_handler = logging.FileHandler("DAP_errors.log", delay=True)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(error_formatter)

base_logger = logging.getLogger()
base_logger.addHandler(error_handler)

import sys
import cli
import sound
import asyncio
import discord
from discord.ext import tasks
from discord.ext import commands
import argparse
import spotiCmds as sp
import json
import spotipy

# commandline args
parser = argparse.ArgumentParser(description="Discord Audio Pipe")
connect = parser.add_argument_group("Command Line Mode")
query = parser.add_argument_group("Queries")
parser.add_argument(
    "-t",
    "--token",
    dest="token",
    action="store",
    default=None,
)
parser.add_argument(
    "-v",
    "--verbose",
    dest="verbose",
    action="store_true",
    help="Enable verbose logging",
)
connect.add_argument(
    "-c",
    "--channel",
    dest="channel",
    action="store",
    type=int,
    help="The channel to connect to as an id",
)
connect.add_argument(
    "-d",
    "--device",
    dest="device",
    action="store",
    type=int,
    help="The device to listen from as an index",
)
query.add_argument(
    "-D",
    "--devices",
    dest="query",
    action="store_true",
    help="Query compatible audio devices",
)
query.add_argument(
    "-C",
    "--channels",
    dest="online",
    action="store_true",
    help="Query servers and channels (requires token)",
)

args = parser.parse_args()
is_gui = not any([args.channel, args.device, args.query, args.online])

# verbose logs
if args.verbose:
    debug_formatter = logging.Formatter(
        fmt="%(asctime)s:%(levelname)s:%(name)s: %(message)s"
    )

    debug_handler = logging.FileHandler(
        filename="discord.log", encoding="utf-8", mode="w"
    )
    debug_handler.setFormatter(debug_formatter)

    debug_logger = logging.getLogger("discord")
    debug_logger.setLevel(logging.DEBUG)
    debug_logger.addHandler(debug_handler)

# don't import qt stuff if not using gui
if is_gui:
    import gui
    from PyQt5.QtWidgets import QApplication, QMessageBox
    global msg
    global dialog
    app = QApplication(sys.argv)
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    dialog = sp.spotTokenEntry()

# main
async def main(bot):
    global spotify
    try:
        # query devices
        if args.query:
            for device, index in sound.query_devices().items():
                print(index, device)

            return

        # check for token
        token = args.token
        try:
            if token is None:
                token = open("token.txt", "r").read()
        except FileNotFoundError:
            if is_gui:
                msg.setWindowTitle("Token Error")
                msg.setText("No Token Provided")
                msg.exec()
            else:
                print("No Token Provided")
        #check for spotify tokens
        try:
            spotify = sp.spotifyLogin()
            spotify.current_user_playing_track()
        except FileNotFoundError: #if they don't exist, grab user's tokens via either gui or cmd line and store in a file
            if is_gui:
                dialog.exec()
                spyC_ID, spyCS_ID, spyR_URL = dialog.getInputs()
            else:
                print("Spotify token details not found, please enter below.")
                spyC_ID = str(input('Spotify Client ID:') )
                spyCS_ID = str(input('Spotify Secret ID:') )
                spyR_URL = str(input('Spotify Redirect URL:') )

            spotToken = {
                    "spotifyClientID": spyC_ID,
                    "spotifySecretID": spyCS_ID,
                    "spotifyRedirect_URL": spyR_URL
                    }
            with open("spotTokens.json", 'w') as outfile:
                json.dump(spotToken, outfile, indent=0)
            spotify = sp.spotifyLogin()
            spotify.current_user_playing_track()

        except spotipy.oauth2.SpotifyOauthError or spotipy.requests.exceptions.HTTPError: #if spotify login fails, notify user and try again.
            msg.setWindowTitle("Spotify Token Error")
            msg.setText("Incorrect token(s) provided. Please reenter tokens/url")
            msg.exec()
            dialog.exec()
            spyC_ID, spyCS_ID, spyR_URL = dialog.getInputs()
            spotToken = {
                    "spotifyClientID": spyC_ID,
                    "spotifySecretID": spyCS_ID,
                    "spotifyRedirect_URL": spyR_URL
                    }
            with open("spotTokens.json", 'w') as outfile:
                json.dump(spotToken, outfile, indent=0)
            spotify = sp.spotifyLogin()
            spotify.current_user_playing_track()
            
        # query servers and channels
        if args.online:
            await cli.query(bot, token)

            return
        
        # GUI
        if is_gui:
            bot_ui = gui.GUI(app, bot)
            asyncio.ensure_future(bot_ui.ready())
            asyncio.ensure_future(bot_ui.run_Qt())
            
        # CLI
        else:
            asyncio.ensure_future(cli.connect(bot, args.device, args.channel))
        await bot.start(token)

    except discord.errors.LoginFailure:
        if is_gui:
            msg.setWindowTitle("Login Failed")
            msg.setText("Please check if the token is correct")
            msg.exec()

        else:
            print("Login Failed: Please check if the token is correct")

    except Exception:
        logging.exception("Error on main")


# run program
intents = discord.Intents.default()
intents.message_content = True
nowPlayingID = None
nowPlayingChannel = None
oldNowPlayingID = None
oldNowPlayingChannel = None


bot = commands.Bot(command_prefix='?', intents = intents)

loop = asyncio.get_event_loop_policy().get_event_loop()

@bot.event
async def on_ready():
    # Waiting until the bot is ready
    await bot.wait_until_ready()
    print(f"Bot is ready!")
    # Starting the loop
    update_activity.start()

@tasks.loop(seconds=5)
async def update_activity():
    '''Updates activity of discord bot, using type listening, with current track name and artist name'''
    global spotEmbed

    spotData = sp.spotAPIcall(spotify,'activity')
    if spotData != None: #if API call has returned data.
        name = f" {spotData.trName} by {spotData.artName}"
        currentAct = discord.Activity(type=discord.ActivityType.listening, name=name)
        await bot.change_presence(activity=currentAct)
        if nowPlayingID != None: #if a current nowplaying message exists, update it.
            spotEmbed = sp.spotAPIcall(spotify,'embed') #call embed creator
            channel = bot.get_channel(nowPlayingChannel) #fetch channel last message existed in
            message = await channel.fetch_message(nowPlayingID) #fetch last embed message
            await message.edit(embed=spotEmbed) #updates last embed message
    else:
        await bot.change_presence(status = None) #if no data from the API call, clear the activity.

@bot.command()
async def np(ctx):
    global nowPlayingID
    global nowPlayingChannel
    global oldNowPlayingID
    global oldNowPlayingChannel

    #global vars are created so update_activity() can access it.
    if nowPlayingID != None: #checks for existing message when called. If no existing message moves on.
        oldNowPlayingID = nowPlayingID
        oldNowPlayingChannel = nowPlayingChannel #stores existing message IDs

    nowPlaying = await ctx.send(embed=spotEmbed) #creates a new message regardless of existing state
    nowPlayingID = nowPlaying.id
    nowPlayingChannel = nowPlaying.channel.id #updates message IDs after creating new msg
    await ctx.message.delete() #deletes ?np command message

    if oldNowPlayingID or oldNowPlayingChannel != None: #if old message exists, fetch then delete it.
        channel = bot.get_channel(oldNowPlayingChannel)
        message = await channel.fetch_message(oldNowPlayingID)
        await message.delete()
    #if no existing message, do nothing.

try:
    loop.run_until_complete(main(bot))

except KeyboardInterrupt:
    print("Exiting...")
    loop.run_until_complete(bot.close())

    # this sleep prevents a bugged exception on Windows
    loop.run_until_complete(asyncio.sleep(1))
    loop.close()