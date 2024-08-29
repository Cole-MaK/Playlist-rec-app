# Playlist-rec-app
This project was created because I hate going through my whole Daylist or Discover Weekly playlists just to go through many songs that I don't like. So I created this app so I could get recommendations based on songs I already like. Just authorize, click on one of your playlists and then the daylist or Discover Weekly and wait for the results :D.

## How to Use?
This application utilizes the Spotify API so you will need to follow these steps:
1. Create an account on Spotify's API site: https://developer.spotify.com/documentation/web-api
2. Go to your dashboard and click "Create app"
  - App name and description don't matter
  - ***make sure in the redirect uri field input: http://127.0.0.1:5000/callback***
3. Once the app is created go into it and click "Settings"
4. Click "View Client Secret"
5. Create a .env file to store the Client ID and Client Secret, it should look like
    CLIENT_ID = '{your client id}'
    SECRET_KEY = '{your client secret}'
