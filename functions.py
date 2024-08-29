from requests import get, post
import json
import os

import pandas as pd
from http.server import HTTPServer
import urllib.parse

from spotifyauthhandler import SpotifyAuthHandler
import threading
import webbrowser

import pkce
import re 

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler

import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv


def generate_code_verifier():
    # Generate a random code_verifier
    code_verifier = pkce.generate_code_verifier(length=128)
    return code_verifier

def generate_code_challenge(code_verifier):
    # Generate the code_challenge from the code_verifier
    code_challenge = pkce.get_code_challenge(code_verifier)
    return code_challenge

def get_Token(auth_code, code_verifier):
    client_id = os.getenv('CLIENT_ID')
    redirect_uri = 'http://127.0.0.1:5000/callback'
    
    url = 'https://accounts.spotify.com/api/token' #post request url

    headers = { # post request headers
        "Content-Type": "application/x-www-form-urlencoded" 
    } 

    data = {'grant_type': 'authorization_code', #post request body
            'code': auth_code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'code_verifier': code_verifier} 

    result = post(url, headers=headers, data = data)
    json_result = json.loads(result.content)
    print(json_result)
    token = json_result['access_token']
    return token

def get_auth_header(token):
   return {'Authorization': 'Bearer ' + token}

def get_user_profile(token):
    url = f'https://api.spotify.com/v1/me'
    header = get_auth_header(token)
    result = get(url, headers = header)
    json_result = json.loads(result.content)
    username = json_result['id']
    return username

def get_user_playlists(token, username):
    url = f'https://api.spotify.com/v1/users/{username}/playlists?limit=50'
    header = get_auth_header(token)
    result = get(url, headers = header)
    json_result = json.loads(result.content)
    playlist_items = {}
    other_items = {}
    for item in json_result['items']:
        if 'daylist' in item['name'] or 'Discover Weekly' in item['name']:
            other_items[item['name']] = item['images'][0]['url']
        elif len(playlist_items) == 30:
            break
        else:
            playlist_items[item['name']] = item['images'][0]['url']
 
    return playlist_items, other_items

def get_user_playlist_id(token, username, playlist_name, playlist_other):
    url = f'https://api.spotify.com/v1/users/{username}/playlists?limit=30&offset=0'
    header = get_auth_header(token)
    result = get(url, headers = header)
    json_result = json.loads(result.content)
    daylist = playlist_other
    playlist_ids = {}
    for i in json_result['items']:
        if playlist_name in i['name']:
            playlist_id = i['id']
            playlist_ids['playlist'] = playlist_id
        elif daylist in i['name']:
            playlist_id = i['id']
            playlist_ids['daylist'] = playlist_id
        else:
            next
    if len(playlist_ids) == 0:
        print('Check name of playlist')
    else:
        return playlist_ids

def get_playlist_data(token, playlist_id):
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    header = get_auth_header(token)
    result = get(url, headers = header)
    json_result = json.loads(result.content)

    song_ids = []
    artist_ids = []
    date_list1 = []
    artist_list1 = []
    song_name_list1 = []
    popular_list1 = []

    for song in json_result['items']:
        song_ids.append(song['track']['id'])
        artist_ids.append(song['track']['artists'][0]['id'])
        date_list1.append(song['track']['album']['release_date'])
        artist_list1.append(song['track']['artists'][0]['name'])
        song_name_list1.append(song['track']['name'])
        popular_list1.append(song['track']['popularity'])

    info = {
        'release_date': date_list1,
        'artists': artist_list1,
        'song': song_name_list1,
        'popularity': popular_list1
    }

    return song_ids, artist_ids, info

def get_audio_feat(token, song_ids):
    song_str = ','.join(song_ids)
    url = f'https://api.spotify.com/v1/audio-features?ids={song_str}'
    header = get_auth_header(token)
    result = get(url, headers = header)
    json_result = json.loads(result.content)
    return json_result['audio_features']

def get_artist_genre(token, id_list):
    header = get_auth_header(token)
    url = f'https://api.spotify.com/v1/artists'
    if len(id_list) > 50:
        id_list_1 = id_list[:len(id_list)//2]
        id_list_2 = id_list[len(id_list)//2:]

        x = get_artist_genre(token, id_list_1)
        y = get_artist_genre(token, id_list_2)
        genre_list = x + y 
        return genre_list
    else:
        id_str = ','.join(id_list)
    query = f'?ids={id_str}'
    url_query = url+query
    
    result = get(url_query, headers=header)
    json_result = json.loads(result.content)['artists']
    genre_list = []
    for artist in json_result:
        genre_list.append(artist['genres'])
    return genre_list

def create_playlist_df(token, playlist_id):
    daylist_song_id, daylist_artist_id, daylist_info = get_playlist_data(token, playlist_id['daylist'])
    playlist_song_id, playlist_artist_id, playlist_info = get_playlist_data(token, playlist_id['playlist']) #max of 100 songs per playlist

    daylist_audio_feat = get_audio_feat(token, daylist_song_id)
    playlist_audio_feat = get_audio_feat(token, playlist_song_id)

    daylist_genre = get_artist_genre(token, daylist_artist_id)
    playlist_genre = get_artist_genre(token, playlist_artist_id)

    daylist_df = pd.DataFrame(daylist_audio_feat)
    daylist_extra_df = pd.DataFrame(daylist_info)

    playlist_df = pd.DataFrame(playlist_audio_feat)
    playlist_extra_df = pd.DataFrame(playlist_info)

    daylist_df = pd.concat([daylist_df, daylist_extra_df], axis=1)
    playlist_df = pd.concat([playlist_df, playlist_extra_df], axis=1)

    daylist_df['genres'] = daylist_genre
    playlist_df['genres'] = playlist_genre

    return daylist_df, playlist_df

def ohe_prep(df, column, new_name): 
    """ 
    Create One Hot Encoded features of a specific column

    Parameters: 
        df (pandas dataframe): Spotify Dataframe
        column (str): Column to be processed
        new_name (str): new column name to be used
        
    Returns:
        tf_df: One hot encoded features 
        
    """
    #simple function to create OHE features
    #this gets passed later on
    
    tf_df = pd.get_dummies(df[column])
    feature_names = tf_df.columns
    tf_df.columns = [new_name + "|" + str(i) for i in feature_names]
    tf_df.reset_index(drop = True, inplace = True)    
    return tf_df

def create_feature_set(df, float_cols):
    """ 
    Process spotify df to create a final set of features that will be used to generate recommendations

    Parameters: 
        df (pandas dataframe): Spotify Dataframe
        float_cols (list(str)): List of float columns that will be scaled 
        
    Returns: 
        final: final set of features 
    """
    
    #tfidf genre lists
    tfidf = TfidfVectorizer()
    tfidf_matrix =  tfidf.fit_transform(df['genres'].apply(lambda x: " ".join(x)))
    genre_df = pd.DataFrame(tfidf_matrix.toarray())
    genre_df.columns = ['genre' + "|" + i for i in tfidf.get_feature_names_out()]
    genre_df.reset_index(drop = True, inplace=True)

    #explicity_ohe = ohe_prep(df, 'explicit','exp')    
    year_ohe = ohe_prep(df, 'year','year') * 0.5
    popularity_ohe = ohe_prep(df, 'popularity_red','pop') * 0.15

    #scale float columns
    floats = df[float_cols].reset_index(drop = True)
    scaler = MinMaxScaler()
    floats_scaled = pd.DataFrame(scaler.fit_transform(floats), columns = floats.columns) * 0.2

    #concanenate all features
    final = pd.concat([genre_df, floats_scaled, popularity_ohe, year_ohe], axis = 1)
     
    #add song id
    final['id']=df['id'].values
    
    return final

def create_necessary_outputs(token, playlist_id, df):
    """ 
    Pull songs from a specific playlist.

    Parameters: 
        playlist_name (str): name of the playlist you'd like to pull from the spotify API
        id_dic (dic): dictionary that maps playlist_name to playlist_id
        df (pandas dataframe): spotify datafram
        
    Returns: 
        playlist: all songs in the playlist THAT ARE AVAILABLE IN THE KAGGLE DATASET
    """
    
    #generate playlist dataframe
    playlist = pd.DataFrame()

    url = f'https://api.spotify.com/v1/playlists/{playlist_id}'
    header = get_auth_header(token)
    result = get(url, headers = header)
    json_result = json.loads(result.content)

    for ix, i in enumerate(json_result['tracks']['items']):
        playlist.loc[ix, 'artist'] = i['track']['artists'][0]['name']
        playlist.loc[ix, 'name'] = i['track']['name']
        playlist.loc[ix, 'id'] = i['track']['id']
        playlist.loc[ix, 'url'] = i['track']['album']['images'][1]['url']
        playlist.loc[ix, 'date_added'] = i['added_at']

    playlist['date_added'] = pd.to_datetime(playlist['date_added'])  
    
    playlist = playlist[playlist['id'].isin(df['id'].values)].sort_values('date_added',ascending = False)
    
    return playlist

def generate_playlist_feature(complete_feature_set, playlist_df, weight_factor):
    """ 
    Summarize a user's playlist into a single vector

    Parameters: 
        complete_feature_set (pandas dataframe): Dataframe which includes all of the features for the spotify songs
        playlist_df (pandas dataframe): playlist dataframe
        weight_factor (float): float value that represents the recency bias. The larger the recency bias, the most priority recent songs get. Value should be close to 1. 
        
    Returns: 
        playlist_feature_set_weighted_final (pandas series): single feature that summarizes the playlist
        complete_feature_set_nonplaylist (pandas dataframe): 
    """
    
    complete_feature_set_playlist = complete_feature_set[complete_feature_set['id'].isin(playlist_df['id'].values)]
    complete_feature_set_playlist = complete_feature_set_playlist.merge(playlist_df[['id','date_added']], on = 'id', how = 'inner')
    complete_feature_set_nonplaylist = complete_feature_set[~complete_feature_set['id'].isin(playlist_df['id'].values)]
    
    playlist_feature_set = complete_feature_set_playlist.sort_values('date_added',ascending=False)

    most_recent_date = playlist_feature_set.iloc[0,-1]
    
    for ix, row in playlist_feature_set.iterrows():
        playlist_feature_set.loc[ix,'months_from_recent'] = int((most_recent_date.to_pydatetime() - row.iloc[-1].to_pydatetime()).days / 30)
        
    playlist_feature_set['weight'] = playlist_feature_set['months_from_recent'].apply(lambda x: weight_factor ** (-x))
    
    playlist_feature_set_weighted = playlist_feature_set.copy()
    playlist_feature_set_weighted.update(playlist_feature_set_weighted.iloc[:,:-4].mul(playlist_feature_set_weighted.weight,0))
    playlist_feature_set_weighted_final = playlist_feature_set_weighted.iloc[:, :-4]
    
    return playlist_feature_set_weighted_final.sum(axis = 0), complete_feature_set_nonplaylist

def generate_playlist_recos(df, features, nonplaylist_features):
    """ 
    Pull songs from a specific playlist.

    Parameters: 
        df (pandas dataframe): spotify dataframe
        features (pandas series): summarized playlist feature
        nonplaylist_features (pandas dataframe): feature set of songs that are not in the selected playlist
        
    Returns: 
        non_playlist_df_top_40: Top 40 recommendations for that playlist
    """
    
    non_playlist_df = df[df['id'].isin(nonplaylist_features['id'].values)]
    non_playlist_df['sim'] = cosine_similarity(nonplaylist_features.drop('id', axis = 1).values, features.values.reshape(1, -1))[:,0]
    non_playlist_df_top_50 = non_playlist_df.sort_values('sim',ascending = False).head(50)
    
    return non_playlist_df_top_50

def generate_recommendation(token, playlist_id, spotify_df_1, spotify_df_2):

    spotify_df = pd.concat([spotify_df_1,spotify_df_2], ignore_index=True)

    spotify_df.drop(columns = [spotify_df.columns[0]], axis = 1, inplace=True)

    spotify_df['year'] = spotify_df['release_date'].apply(lambda x: x.split('-')[0])

    float_cols = spotify_df.dtypes[spotify_df.dtypes == 'float64'].index.values

    ohe_cols = 'popularity'
    # create 5 point buckets for popularity 
    spotify_df['popularity_red'] = spotify_df['popularity'].apply(lambda x: int(x/5))

    complete_feature_set = create_feature_set(spotify_df, float_cols=float_cols)

    playlist = create_necessary_outputs(token, playlist_id['playlist'], spotify_df)

    complete_feature_set_playlist_vector, complete_feature_set_nonplaylist = generate_playlist_feature(complete_feature_set, playlist, 1.09)

    top10 = generate_playlist_recos(spotify_df, complete_feature_set_playlist_vector, complete_feature_set_nonplaylist)
    
    top10.index += 1
     
    return top10[['artists','song','sim']]
