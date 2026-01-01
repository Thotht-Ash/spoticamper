#!/usr/bin/env python

from bs4 import BeautifulSoup as bs
from ratelimit import limits, sleep_and_retry
from tqdm import tqdm
import requests
import re
import base64
import os
import urllib
import json
import argparse


# limit to 5 calls per second
@sleep_and_retry
@limits(calls=5, period=1)
def search_bandcamp_album_url(artist, album):
    params = urllib.parse.urlencode({"q": f"{artist} {album}"})
    res = requests.get(f"https://bandcamp.com/search?{params}")

    soup = bs(res.content, "html.parser")
    search_results = soup.select(".searchresult")
    if len(search_results) != 0:
        link = urllib.parse.urlparse(search_results[0].select("a[href]")[0]['href'])
        return f"https://{link.netloc}{link.path}"
    else:
        return ""

def get_spotify_auth_token():
    basic_token = base64.b64encode(f"{os.environ['SPOTIFY_APP_ID']}:{os.environ['SPOTIFY_APP_SECRET']}".encode()).decode()
    return requests.post(
        url="https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {basic_token}"},
        data={"grant_type": "client_credentials"}
    ).json()["access_token"]

def get_spotify_playlist(token, id):
    res = requests.get(
        url=f"https://api.spotify.com/v1/playlists/{id}?fields=tracks.items(track(artists(name), album(id,name)))",
        headers={"Authorization": f'Bearer {token}'}
    )
    return res.json()['tracks']['items']

def get_bandcamp_purchases():
    res = requests.get(
            url=f"https://bandcamp.com/{os.environ['BANDCAMP_USERNAME']}",
            headers={"Cookie": f"identity={os.environ['BANDCAMP_TOKEN']}"}
    )
    soup = bs(res.content, "html.parser")

    links = []
    for item in soup.select(".item-link"):
        if "href" in item.attrs.keys():
            links.append(item["href"])
    return links


def load_state():
    try:
        with open("state.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("generating new state...")
        return {"albums": {}, "bandcamp_url_to_album_key":{}}

def dump_state(state):
    with open("state.json", "w") as f:
         json.dump(state, f)

def bandcamp_refresh_purchased(state):
    # get purchases and mark any spotify albums in state as purchased
    bandcamp_purchases = get_bandcamp_purchases()
    new_purchase_count = 0
    for url in bandcamp_purchases:
        if url in state["bandcamp_url_to_album_key"]:
            if not state["albums"][state["bandcamp_url_to_album_key"][url]]["purchased"]:
                state["albums"][state["bandcamp_url_to_album_key"][url]]["purchased"] = True
                new_purchase_count += 1

    print(f"{new_purchase_count} albums newly registered as purchased")
    return state


def get_cli_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-p", "--playlist", action="store", help="spotify playlist URL")
    argparser.add_argument("-u", "--unpurchased", action="store_true", help="print a list of URLs for all unpurchased albums")
    argparser.add_argument("-s", "--stats", action="store_true", help="print stats")
    argparser.add_argument("-r", "--refresh_purchased", action="store_true", help="refresh which albums are purchased from bandcamp")
    return argparser.parse_args()

def pull_spotify_playlist(state, cli_args):
    # retreive spotify token from envvar creds
    s_token = get_spotify_auth_token()

    # get the playlist
    parsed_playlist_url = urllib.parse.urlparse(cli_args.playlist)
    playlist = get_spotify_playlist(s_token, os.path.split(parsed_playlist_url.path)[-1])

    # load any new tracks into state
    registered_album_count = 0
    for track in playlist:
        album = track["track"]["album"]
        album_key = f"{album['name']}:{album['id']}"

        if not album_key in state["albums"]:
            artists = []
            for artist in track["track"]["artists"]:
                artists.append(artist["name"])

            state["albums"][album_key] = {
                    "key": album_key,
                    "id": album["id"],
                    "name": album["name"],
                    "artists": artists,
                    "purchased": False,
                    "bandcamp_search_term": f"{artists[0]} {album['name']}",
                    "bandcamp_url_found": False,
                    "bandcamp_url_searched": False,
                    "bandcamp_url": ""
            }
            registered_album_count += 1

    print(f"registered {registered_album_count} albums from spotify")

    # find all bandcamp listings we can for albums missing bandcamp urls (w

    unsearched_count = 0
    for album in state["albums"].values():
        if not album["bandcamp_url_searched"]:
            unsearched_count += 1

    progress = tqdm(total=unsearched_count, desc="")
    for album in state["albums"].values():
        if not album["bandcamp_url_searched"]:
            bandcamp_url = search_bandcamp_album_url(album["artists"][0], album["name"])
            album["bandcamp_url_searched"] = True
            if bandcamp_url != "":
                album["bandcamp_url_found"] = True
                album["bandcamp_url"] = bandcamp_url

                state["bandcamp_url_to_album_key"][bandcamp_url] = album["key"]
            state["albums"][album["key"]] = album

            progress.update(1)
            progress.set_description(bandcamp_url)

    # get purchases and mark any spotify albums in state as purchased
    state = bandcamp_refresh_purchased(state)

    return state

def print_unpurchased(state):
    for album in state["albums"].values():
        if not album["purchased"] and album["bandcamp_url_found"]:
            print(album["bandcamp_url"])

def print_stats(state):
    album_count = 0
    purchased_count = 0
    url_found_count = 0
    url_searched_count = 0
    for album in state["albums"].values():
        album_count += 1
        if album["purchased"]:
            purchased_count += 1
        if album["bandcamp_url_found"]:
            url_found_count += 1
        if album["bandcamp_url_searched"]:
            url_searched_count += 1
    url_not_found_count=album_count-url_found_count

    print(f"albums registered from spotify: {album_count}")
    print(f"albums purchased on bandcamp: {purchased_count}")
    print(f"albums found on bandcamp: {url_found_count} (missing {url_not_found_count} bandcamp URLs)")
    print(f"{album_count-url_searched_count} albums haven't been bandcamp searched for some reason")
    print(f"{(purchased_count/album_count)*100}% purchased")
    print(f"{(url_not_found_count/album_count)*100}% not found")



# load state
state = load_state()

# get CLI args
cli_args = get_cli_args()

if cli_args.playlist:
    state = pull_spotify_playlist(state, cli_args)

if cli_args.unpurchased:
    print_unpurchased(state)

if cli_args.stats:
    print_stats(state)

if cli_args.refresh_purchased:
    state = bandcamp_refresh_purchased(state)

# dump state back to state.json
dump_state(state)


