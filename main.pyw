import argparse
import asyncio
import logging
import sys
from os import environ
from pathlib import Path

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from PyQt5.QtWidgets import QInputDialog
from spotipy import oauth2

import cli
import sound
import spoticmds as sp

# Determine base directory (works for both frozen exe and script)
base_dir = Path(sys.argv[0]).parent if getattr(sys, "frozen", False) else Path(__file__).parent

# error logging
error_formatter = logging.Formatter(
    fmt="%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

error_handler = logging.FileHandler("DAP_errors.log", delay=True)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(error_formatter)

base_logger = logging.getLogger()
base_logger.addHandler(error_handler)

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
        fmt="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    )

    debug_handler = logging.FileHandler(
        filename="discord.log", encoding="utf-8", mode="w",
    )
    debug_handler.setFormatter(debug_formatter)

    debug_logger = logging.getLogger("discord")
    debug_logger.setLevel(logging.DEBUG)
    debug_logger.addHandler(debug_handler)

# don't import qt stuff if not using gui
if is_gui:
    from PyQt5.QtWidgets import QApplication, QMessageBox

    import gui
    global msg
    global dialog
    app = QApplication(sys.argv)
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information) #sets up general gui interface for any queries.
    dialog = sp.spotTokenEntry() #defines global dialog based on token entry function

# main
async def main(bot):
    global spotify
    try:
        # query devices
        if args.query:
            for device, index in sound.query_devices().items():
                print(index, device)
            return

        load_dotenv(base_dir / "tokens.env")

        # Get Discord token
        token = environ.get("DISCORD")
        if token is None:
            error_msg = "No DISCORD token found in environment"
            if is_gui:
                msg.setWindowTitle("Discord Token Error")
                msg.setText(error_msg)
                msg.exec()

                # Show dialog for Discord token
                discord_token, ok = QInputDialog.getText(None, "Discord Token", "Enter your Discord bot token:")

                if ok and discord_token:
                    sp.save_tokens_to_env(base_dir / "tokens.env", {"DISCORD": discord_token})
                    load_dotenv(base_dir / "tokens.env")
                    token = discord_token
                else:
                    return
            else:
                print(error_msg)
                return

        # Login to Spotify BEFORE Discord
        spotify = sp.spotify_login_with_dialog(msg, base_dir, is_gui=is_gui)
        if spotify is None:
            return
        spotify.current_user_playing_track()
        print("Spotify login successful")

        # query servers and channels
        if args.online:
            await cli.query(bot, token)
            return

        # GUI
        if is_gui:
            bot_ui = gui.GUI(app, bot)
            asyncio.create_task(bot_ui.ready())
            asyncio.create_task(bot_ui.run_Qt())

        # CLI
        else:
            asyncio.create_task(cli.connect(bot, args.device, args.channel))

            asyncio.ensure_future(cli.connect(bot, args.device, args.channel))
        await bot.start(token)

    except discord.errors.LoginFailure:
        error_msg = "Please check if the token is correct"
        if is_gui:
            msg.setWindowTitle("Login Failed")
            msg.setText(error_msg)
            msg.exec()
        else:
            print("Login Failed: " + error_msg)

    except asyncio.CancelledError:
        if is_gui:
            bot_ui.close()

        await bot.close()
        await asyncio.sleep(1)
        raise

    except Exception:
        base_logger.exception("Error on main")



# run program
c_intents = discord.Intents.default()
c_intents.message_content = True
bot = discord.Client(command_prefix="?",intents=c_intents)

nowPlayingID = None
nowPlayingChannel = None
oldNowPlayingID = None
oldNowPlayingChannel = None
firstCall = True

try:
    loop = asyncio.get_event_loop()
except RuntimeError as e:
    if str(e).startswith("There is no current event loop in thread"):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    else:
        raise

@bot.event
async def on_ready():
    # Waiting until the bot is ready
    await bot.wait_until_ready()
    print("Bot is ready!")
    # # Starting the loop
    update_activity.start()

@tasks.loop(seconds=10)
async def update_activity():
    '''Updates embed every 10 seconds, if the embed exists'''
    try:
        if nowPlayingID != None: #if a current nowplaying message exists, update it.
            spotEmbed = sp.spotAPIcall(spotify,'embed') #creates the embed
            channel = bot.get_channel(nowPlayingChannel) #fetch channel last message existed in
            message = await channel.fetch_message(nowPlayingID) #fetch last embed message
            await message.edit(embed=spotEmbed) #updates last embed message
    except discord.errors.NotFound:
        print("Failed, will retry")
        
@bot.command()
#Main definition for the np command, which aims to display current information.
async def np(ctx):
    global nowPlayingID
    global nowPlayingChannel
    global oldNowPlayingID
    global oldNowPlayingChannel
    
    spotEmbed = sp.spotAPIcall(spotify,'embed') #creates the embed
    
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

@bot.command()
#Main definition for the leave command, which tells the bot to disconnect but also deletes the last np message.
async def leave(ctx):
    print("test")
    

try:
    asyncio.run(main(bot))
except KeyboardInterrupt:
    print("Exiting...")
    loop.run_until_complete(bot.close())

    # this sleep prevents a bugged exception on Windows
    loop.run_until_complete(asyncio.sleep(1))
finally:
    loop.close()