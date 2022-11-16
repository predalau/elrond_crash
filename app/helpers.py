from time import sleep
from json import loads
from vars import DELAY
from cloudscraper import create_scraper

scraper = create_scraper()


def get_http_request(url):
    req = scraper.get(url)
    sleep(DELAY)
    return req


def check_player_balance(address, balance):
    req_url = f"https://api.elrond.com/accounts/{address}"
    req = get_http_request(req_url)
    req = loads(req)
    if "balance" in req.keys():
        balance_now = float(req["balance"])
        actual_balance = balance_now / (10 ** 18)
        return (balance == actual_balance) or (balance == balance_now)
    else:
        return False
