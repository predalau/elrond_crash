import requests

# from vars import CLIENT_ID, CLIENT_SECRE

API_ENDPOINT = 'https://discord.com/api'
CLIENT_ID = '1042162577175756841'
CLIENT_SECRET = 'wNgPZfb8NzvWVpVFIsgRhRJAxVRax7P9'
REDIRECT_URI = 'https://squid-app-tkgbl.ondigitalocean.app/discordAuth'


def exchange_code(code):
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    r = requests.post('%s/oauth2/token' % API_ENDPOINT, data=data, headers=headers)
    print(r.content)
    r.raise_for_status()
    return r.json()


def refresh_token(refresh_token):
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    r = requests.post('%s/oauth2/token' % API_ENDPOINT, data=data, headers=headers)
    r.raise_for_status()
    return r.json()


def get_token():
    data = {
        'grant_type': 'client_credentials',
        'scope': 'identify connections'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    r = requests.post('%s/oauth2/token' % API_ENDPOINT, data=data, headers=headers, auth=(CLIENT_ID, CLIENT_SECRET))
    r.raise_for_status()
    return r.json()


def get_user_data(token):
    endpoint = "https://discord.com/api/v10/users/@me"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        "Authorization": f"Bearer {token}",
    }
    req = requests.get(endpoint, headers=headers)
    print(req.content)
    req.raise_for_status()
    return req.json()


def get_user_avatar(avt: str):
    root = "https://cdn.discordapp.com/"
    return root
