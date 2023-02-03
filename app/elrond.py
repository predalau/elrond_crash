import requests
from fastapi.exceptions import HTTPException
from erdpy.accounts import Account, Address
from erdpy.proxy import ElrondProxy
from erdpy.transactions import Transaction  # , BunchOfTransactions
from erdpy import config
from vars import CHAIN_ID, SC_ADDRESS, ELROND_GATEWAY, ELROND_API
import asyncio
import logging

logger = logging.getLogger("fastapi")
logger.setLevel(logging.DEBUG)


sc_gateway = ""
if CHAIN_ID == "D":
    sc_gateway = f"https://devnet-gateway.multiversx.com"
elif CHAIN_ID == "T":
    sc_gateway = f"https://testnet-gateway.elrond.com"  # /address/{SC_ADDRESS}/keys"
else:
    sc_gateway = f"https://api.multiversx.com"  # address/{SC_ADDRESS}/keys"


def get_proxy_and_account():
    proxy = ElrondProxy(ELROND_GATEWAY)
    account = Account(pem_file="wallet.pem")
    account.sync_nonce(proxy)
    return proxy, account


elrond_proxy, elrond_account = get_proxy_and_account()


def int_to_hex(number: int) -> str:
    hex_nr = hex(number)[2:]
    if len(hex_nr) % 2 != 0:
        hex_nr = "0" + hex_nr
    return hex_nr


def get_all_bets():
    sc = ELROND_GATEWAY + "/address/" + SC_ADDRESS + "/keys"
    bet_funds_hex = "bet_funds.mapped".encode().hex()
    next_bet_funds_hex = "next_bet_funds.mapped".encode().hex()
    storage = requests.get(sc)

    try:
        storage.raise_for_status()
        storage = storage.json()["data"]["pairs"]
    except HTTPException:
        print("Bad request:\t", storage.content)

    bet_funds = {
        Address(key.replace(bet_funds_hex, "")).bech32(): int(value, 16) / pow(10, 18)
        for key, value in storage.items()
        if bet_funds_hex in key and next_bet_funds_hex not in key
    }
    return bet_funds


def get_all_rewards():
    sc = ELROND_GATEWAY + "/address/" + SC_ADDRESS + "/keys"
    reward_funds_hex = "reward_funds.mapped".encode().hex()
    storage = requests.get(sc).json()["data"]["pairs"]
    reward_funds = {
        Address(key.replace(reward_funds_hex, "")).bech32(): int(value, 16) / pow(10, 18)
        for key, value in storage.items()
        if reward_funds_hex in key
    }
    print(reward_funds)


def place_bet(sender: Account, amount):
    tx = Transaction()
    tx.nonce = sender.nonce
    tx.sender = sender.address.bech32()
    tx.value = str(int(amount * pow(10, 18)))
    tx.receiver = SC_ADDRESS
    tx.gasPrice = 1000000000
    tx.chainID = CHAIN_ID
    tx.data = "addBetFunds"
    tx.gasLimit = 6000000
    tx.version = config.get_tx_version()
    tx.sign(sender)
    sent_tx = tx.send_wait_result(elrond_proxy, timeout=60)
    print(sent_tx)


def send_rewards(sender: Account, adds: dict):
    tx = Transaction()
    tx.nonce = sender.nonce
    tx.sender = sender.address.bech32()
    tx.value = str(int(0.00 * pow(10, 18)))
    tx.receiver = SC_ADDRESS
    tx.gasPrice = min(6000000000, 6000000000 * (len(adds) + 1))
    tx.chainID = CHAIN_ID
    tx.data = "multiplyFunds"
    for address, multiplier in adds.items():
        mult_str = int(f"{round(multiplier, 2):.2f}".replace(".", ""))
        mult_str = int_to_hex(mult_str)
        tx.data += "@" + Address(address).hex() + "@" + mult_str
    tx.gasLimit = (len(adds.keys()) + 1) * 6000000
    tx.version = config.get_tx_version()
    tx.sign(sender)
    sent_tx = tx.send(elrond_proxy)
    logging.info(f"Endgame rewards transaction:\t{sent_tx}", extra=sent_tx)
    return sent_tx


async def confirm_transaction(txHash: str):
    endpoint = ELROND_API + f"/transactions/{txHash}"
    while True:
        await asyncio.sleep(2)
        response = requests.get(endpoint)
        if response.status_code == 200:
            response = response.json()
            status = response["status"]
            if status == "pending":
                continue
            elif status == "success":
                return True
            else:
                print(response.json())
                return False
        else:
            logger.info(f"Bad request confirming endgame tx:\t{endpoint}", extra=response.json())