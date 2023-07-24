from time import strftime
from time import gmtime
from datetime import datetime
import discord
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PyQt5.QtWidgets import QDialog, QLineEdit, QFormLayout, QDialogButtonBox, QMessageBox
import json

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

def spotifyLogin():

    with open("spotTokens.json", 'r') as j: #load tokens if they exist
                spotToken = json.loads(j.read())
    '''Grabs tokens from given file. Connects to spotify API.'''
    spotTokenDict = spotToken

    spyC_ID = spotTokenDict['spotifyClientID']
    spyCS_ID = spotTokenDict['spotifySecretID']
    spyR_URL = spotTokenDict['spotifyRedirect_URL']
        
    scope = "user-read-currently-playing user-read-playback-state"
    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(spyC_ID,spyCS_ID,spyR_URL,scope=scope)) #authenticates with SpotifyOAuth method.
    
    return spotify

def spotDataExtract(currentTrack, nextTrack):
    '''Using fetched API data, returns formatted data types accessible to the embed creator.
    Uses spot Class for neat output'''

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

    if type == 'activity': #if type is to update bot activity, and something is playing, fetch the data, update the global vars and return data to update_activity
        if currentTrack != None:
            spotData = spotDataExtract(currentTrack,nextTrack)
            if spotData != None:
                lastTrName = spotData.trName
                lastArtName = spotData.artName
                lastAlbArt = spotData.albArt
                return spotData
            else:
                return None
        else:
            return None #else, return none
    elif type == 'embed': #if type is to update embed, and something is playing, fetch data update global vars and return embed to update_activity or np command.
        if currentTrack != None:
            spotData = spotDataExtract(currentTrack,nextTrack)
            if spotData != None:
                lastTrName = spotData.trName
                lastArtName = spotData.artName
                lastAlbArt = spotData.albArt
                return createPlayingEmbed(spotData)
        else: #else if something is not playing, create the not playing embed and return this to update_activity or np command.
            return createNotPlayingEmbed()
    
