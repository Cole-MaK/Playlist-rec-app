from requests import post, get
from flask import Flask, render_template, request, redirect, url_for, session, render_template_string
from functions import *


app = Flask(__name__) # initialize flask
app.secret_key = os.getenv('SECRET_KEY') # set secret key in .env file

@app.route('/') # decorators
@app.route('/home')
def home_page():

    client_id = os.getenv('CLIENT_ID')
    redirect_uri = 'http://127.0.0.1:5000/callback' #'https://daylist-rec-app-0400112ba358.herokuapp.com/callback'
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    url = 'https://accounts.spotify.com/authorize' #get request url

    params = { #get request body
        'client_id': client_id,
        'response_type':'code',
        'redirect_uri': redirect_uri,
        'scope': 'playlist-read-private user-read-email',
        'code_challenge_method': 'S256',
        'code_challenge': code_challenge
    }

    auth_url_with_params = f"{url}?{urllib.parse.urlencode(params)}"

    session['code-verifier'] = code_verifier

    return render_template('index.html', url=auth_url_with_params)


@app.route('/callback')
def callback():

    auth_code = request.args.get('code')
    code_verifier = session.get('code-verifier', 'No data found')
    token = get_Token(auth_code, code_verifier)
    session['token'] = token

    username = get_user_profile(token)
    session['username'] = username
    
    playlist_items, other_items = get_user_playlists(token, username)

    return render_template('result.html', playlist_items = playlist_items, other_items = other_items)

@app.route('/recommend', methods=['POST'])
def recommend():

    token = session.get('token')
    username = session.get('username')

    playlist_name = request.form['selected_playlist']
    playlist_other = request.form['selected_playlist-compare']

    playlist_id = get_user_playlist_id(token, username, playlist_name, playlist_other)
    daylist_df, playlist_df = create_playlist_df(token, playlist_id)

    df = generate_recommendation(token, playlist_id, daylist_df, playlist_df)

    return render_template('recommend.html', tables=[df.to_html(classes='data')], titles=df.columns.values)


if __name__ == '__main__':
    app.run()