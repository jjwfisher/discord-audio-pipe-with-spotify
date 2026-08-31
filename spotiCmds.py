from datetime import datetime
from os import environ
from pathlib import Path
from time import gmtime, strftime

import discord
import spotipy
from dotenv import load_dotenv, set_key
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox
from spotipy.oauth2 import SpotifyOAuth

firstCall = True

class spotTokenEntry(QDialog):
    '''Custom input window for spotify API details if not already given.'''
    def __init__(self):
        super().__init__()

        self.spCliID = QLineEdit(self)
        self.spSecID = QLineEdit(self)
        self.spRedirURL = QLineEdit(self)
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self);

        layout = QFormLayout(self)
        layout.addRow("Spotify Client ID", self.spCliID)
        layout.addRow("Spotify Secret ID", self.spSecID)
        layout.addRow("Spotify Redirect URL", self.spRedirURL)
        layout.addWidget(buttonBox)
        
        self.setWindowTitle("Please enter your Spotify API Details")

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def getInputs(self):
        return (self.spCliID.text(), self.spSecID.text(), self.spRedirURL.text())

class spot:
    '''Provides clearer storage of variables from the Spotify API'''
    def __init__(self, trName, albArt, trProg, trDur, trUrl, artName, nxtArtName, nxtTrName):
        self.trName = trName
        self.albArt = albArt
        self.trProg = trProg
        self.trDur = trDur
        self.trUrl = trUrl
        self.artName = artName
        self.nxtArtName = nxtArtName
        self.nxtTrName = nxtTrName

callNum = 0

def save_tokens_to_env(env_file_path: str, token_dict: dict) -> None:
    """Save tokens to .env file."""
    for key, value in token_dict.items():
        set_key(env_file_path, key, value)

def spotifyLogin():
    """Grabs tokens from given file. Connects to spotify API with auto-refresh."""
    try:
        spot_cid = environ["SPOT_CID"]
        spot_sid = environ["SPOT_SID"]
        spot_uri = environ["SPOT_URI"]
    except KeyError as kde:
        msg = "Could not find tokens."
        raise KeyError(msg) from kde

    scope = "user-read-currently-playing,user-read-playback-state"
    cache_path = ".cache"

    try:
        auth_manager = SpotifyOAuth(
            client_id=spot_cid,
            client_secret=spot_sid,
            redirect_uri=spot_uri,
            scope=scope,
            cache_path=cache_path,
            show_dialog=False,  # Auto-refresh without user intervention
        )
        return spotipy.Spotify(auth_manager=auth_manager)
    except spotipy.oauth2.SpotifyOauthError as e:
        if "invalid_grant" in str(e) or "Refresh token revoked" in str(e):
            # Clear cache and force re-auth
            if Path.exists(cache_path):
                Path.unlink(cache_path)
            auth_manager = SpotifyOAuth(
                client_id=spot_cid,
                client_secret=spot_sid,
                redirect_uri=spot_uri,
                scope=scope,
                cache_path=cache_path,
                show_dialog=True,  # Show auth dialog on revoked token
            )
            return spotipy.Spotify(auth_manager=auth_manager)
        raise

def spotify_login_with_dialog(msg: "QMessageBox", base_dir: Path, *, is_gui: bool = True) -> spotipy.Spotify | None:
    """Handle Spotify login with dialog prompts for missing/invalid tokens.

    Attempts to login to Spotify, and if tokens are missing, prompts the user
    via a GUI dialog to enter them. Saves the tokens to the .env file and retries.

    Args:
        msg: QMessageBox instance for displaying GUI dialogs.
        base_dir: Path to base directory where tokens.env is located.
        is_gui: Whether running in GUI mode (default: True).

    Returns:
        Spotify API object if successful, None if user cancelled or error occurred.

    """
    # First attempt
    try:
        return spotifyLogin()
    except KeyError:
        pass  # Handle below

    # KeyError: tokens missing
    if is_gui:
        msg.setWindowTitle("No Spotify Tokens Found")
        msg.setText("Please enter your Spotify API credentials")
        msg.exec()

        token_dialog = spotTokenEntry()
        if not token_dialog.exec_():
            return None

        client_id, secret_id, redirect_url = token_dialog.getInputs()
        if not (client_id and secret_id and redirect_url):
            msg.setWindowTitle("Error")
            msg.setText("All fields are required")
            msg.exec()
            return None

        save_tokens_to_env(
            base_dir / "tokens.env",
            {
                "SPOT_CID": client_id,
                "SPOT_SID": secret_id,
                "SPOT_URI": redirect_url,
            },
        )
        load_dotenv(base_dir / "tokens.env")
    else:
        print("Spotify tokens not found")
        return None

    # Retry once after saving tokens
    try:
        return spotifyLogin()
    except spotipy.oauth2.SpotifyOauthError as e:
        if is_gui:
            msg.setWindowTitle("Spotify Login Failed")
            msg.setText(str(e))
            msg.exec()
        else:
            print(f"Spotify login error: {e}")
        return None

def spotDataExtract(currentTrack, nextTrack):
    """Use fetched API data, returns formatted data types accessible to the embed creator.

    Uses spot Class for neat output.
    """
    trackInfo = currentTrack['item'] #removes common header
    try:
        trackName = trackInfo['name'] #index 0
        albumArt = trackInfo['album']['images'][0]['url'] #index 1
        trackProgress = round(currentTrack['progress_ms']/1000) #in s / index 2
        trackDuration = round(trackInfo['duration_ms']/1000) #in s / index 3
        trackUrl = trackInfo['external_urls']['spotify'] #index 4
        artistName = trackInfo['artists'][0]['name'] #index 5
        nextArtistName = nextTrack['queue'][0]['artists'][0]['name'] #index 6
        nextTrackName = nextTrack['queue'][0]['name'] #index 7
        spotData = spot(trackName, albumArt, trackProgress,trackDuration,trackUrl,artistName, nextArtistName, nextTrackName)
        return spotData
    except(TypeError):
        return None
    except(IndexError):
        return None
    

def createNotPlayingEmbed():
    '''If Spotify is not currently open, creates a different embed message stating as such. Functionality to remember last song that DAP saw.'''
    if lastTrName != None and lastArtName != None:
        embed = discord.Embed(title="Spotify is not playing!",
                      description=f"__Last Played:__\n**Song:** {lastTrName} \n\n **Artist:** {lastArtName} " ,
                      colour=0xa61717,
                      timestamp=datetime.now())
        embed.set_thumbnail(url=lastAlbArt)
        embed.set_footer(text="Forked by @EarthFishy, created by @QiCuiHub")
        return embed
    else:
        embed = discord.Embed(title="Spotify is not playing!",
                      description=f"__Last Played:__\n**Song:** Unknown \n\n **Artist:** Unknown " ,
                      colour=0xa61717,
                      timestamp=datetime.now())
        embed.set_footer(text="Forked by @EarthFishy, created by @QiCuiHub")
        return embed

#nowplaying embed
def createPlayingEmbed(spotData):
    '''If Spotify is open and playing, created an embed string displaying current and next queued track info.'''

    trackProgressStr = strftime('%#M:%S', gmtime(spotData.trProg)) #used to convert s int to a formatted str.
    trackDurationStr = strftime('%#M:%S', gmtime(spotData.trDur))

    embed = discord.Embed(title="Now Playing on Spotify:",
                    description=f"**Song:** {spotData.trName} \n\n :arrow_forward: {trackProgressStr} / {trackDurationStr} :arrow_backward: \n\n **Artist:** {spotData.artName} \n \n {spotData.trUrl}", 
                    colour=0xa61717,
                    timestamp=datetime.now())

    embed.add_field(name="Next in the queue: \n", value=f"{spotData.nxtTrName} by {spotData.nxtArtName}")

    embed.set_thumbnail(url=spotData.albArt)

    embed.set_footer(text="Forked by @EarthFishy, created by @QiCuiHub")

    return embed

def spotAPIcall(spotify, type):
    '''Main calling function used by main.pyw
    Sets global variables:
    lastTrName, lastArtName, lastAlbArt - these are a local cache so that when Spotify is not playing, createNotPlayingEmbed can inform the user what was playing if the information is avaliable.
    firstCall ensures that the initialisation of the above vars only happens once.'''
    global lastTrName
    global lastArtName
    global lastAlbArt
    global firstCall

    if firstCall: #if first run, initialises the cache variables.
        lastTrName = None
        lastArtName = None
        lastAlbArt = None
        firstCall = False
    
    currentTrack = spotify.current_user_playing_track()
    nextTrack = spotify.queue()
    #above fetches current data

    # if type == 'activity': #if type is to update bot activity, and something is playing, fetch the data, update the global vars and return data to update_activity
    #     if currentTrack != None:
    #         spotData = spotDataExtract(currentTrack,nextTrack)
    #         if spotData != None:
    #             lastTrName = spotData.trName
    #             lastArtName = spotData.artName
    #             lastAlbArt = spotData.albArt
    #             return spotData
    #         else:
    #             return None
    #     else:
    #         return None #else, return none
    #type == 'embed': #if type is to update embed, and something is playing, fetch data update global vars and return embed to update_activity or np command.
    if currentTrack != None:
        spotData = spotDataExtract(currentTrack,nextTrack)
        if spotData != None:
            lastTrName = spotData.trName
            lastArtName = spotData.artName
            lastAlbArt = spotData.albArt
            return createPlayingEmbed(spotData)
    else: #else if something is not playing, create the not playing embed and return this to update_activity or np command.
        return createNotPlayingEmbed()