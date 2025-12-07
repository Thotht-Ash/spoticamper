# spoticamper
this is a personal script I'm sharing for mass purchasing music in spotify playlists on bandcamp.

At the moment, it does its best to search for music in a provided spotify playlist and registers any new albums into a json store kept in the project directory. It then scrapes bandcamp for the bandcamp URLs of newly registered albums and using your bandcamp auth, determines which of them have not already been purchased.

There are several utility commands for printing information from the json store to get statistics, list unpurchased albums, etc. viewable via `-h`

# setup
```bash
# clone repo
git clone 'git@github.com:zoefiri/spoticamper.git'
cd spoticamper 

# setup venv stuff
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

# usage 
### making a spotify app
you will need to make a spotify app to use this script, you can do this @ https://developer.spotify.com/dashboard.
You can fill the fields out with anything you want, select "Web API" for API usage. 

Once you've created your app save the client ID & secret somewhere safe

### getting your bandcamp auth token
honestly, this is kind of sketchy and there's probably a better way to do this but, open the network tab in bandcamp.com while logged in and go to any bandcamp.com request, rip the value of the `identity` cookie and keep it somewhere safe (I have no idea how quickly this thing expires, you'll probably have to do this frequently).

### set envvars
- `SPOTIFY_APP_ID`: spotify app client ID
- `SPOTIFY_APP_SECRET`: spotify app client secret
- `BANDCAMP_TOKEN`: the bandcamp auth token you ripped from the network tab
- `BANDCAMP_USERNAME`: your bandcamp username

### some basic commands
```bash
# help txt
./spoticamper.py -h

# run script
./spoticamper.py -p 'https://open.spotify.com/playlist/...'

# print stats or list unpurchased tracks
./spoticamper.py -p
./spoticamper.py -s

# refresh purchased tracks from bandcamp collection
./spoticamper.py -r
```
