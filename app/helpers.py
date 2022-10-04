from time import sleep

# import pandas as pd
import cloudscraper
from datetime import datetime, timedelta
from discord import Embed, Webhook, RequestsWebhookAdapter
from bs4 import BeautifulSoup
from vars import *
import json
import threading

scraper = cloudscraper.create_scraper()


async def game_logic():
    try:
        await asyncio.sleep(3)
        print("hello!")
    except Exception as e:
        print(str(e))


def get_http_request(url):
    req = scraper.get(url)
    sleep(DELAY)
    return req.text


def check_player_balance(address, balance):
    req_url = f"https://api.elrond.com/accounts/{address}"
    req = get_http_request(req_url)
    req = json.loads(req)
    if "balance" in req.keys():
        balance_now = float(req["balance"])
        actual_balance = balance_now / (10**18)
        return (balance == actual_balance) or (balance == balance_now)
    else:
        return False
