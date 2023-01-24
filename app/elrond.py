import requests
from erdpy.accounts import Account, Address
from erdpy.proxy import ElrondProxy
from erdpy.transactions import Transaction  # , BunchOfTransactions
from erdpy import config
from vars import CHAIN_ID, SC_ADDRESS
import asyncio
import logging
from fastapi import HTTPException

logger = logging.getLogger("fastapi")

sc_gateway = ""
if CHAIN_ID == "D":
    sc_gateway = f"https://devnet-api.elrond.com"
elif CHAIN_ID == "T":
    sc_gateway = f"https://testnet-gateway.elrond.com"  # /address/{SC_ADDRESS}/keys"
else:
    sc_gateway = f"https://api.multiversx.com"  # address/{SC_ADDRESS}/keys"


def get_proxy_and_account():
    elrond_proxy = ElrondProxy(sc_gateway)
    elrond_account = Account(pem_file="wallet.pem")
    elrond_account.sync_nonce(elrond_proxy)
    return elrond_proxy, elrond_account


elrond_proxy, elrond_account = get_proxy_and_account()


def int_to_hex(number: int) -> str:
    hex_nr = hex(number)[2:]
    if len(hex_nr) % 2 != 0:
        hex_nr = "0" + hex_nr
    return hex_nr


def get_all_bets():
    sc = sc_gateway + "/address/" + SC_ADDRESS + "/keys"
    bet_funds_hex = "bet_funds.mapped".encode().hex()
    next_bet_funds_hex = "next_bet_funds.mapped".encode().hex()
    storage = requests.get(sc)
    if storage.status_code == 200:
        storage = storage.json()["data"]["pairs"]
        bet_funds = {
            Address(key.replace(bet_funds_hex, "")).bech32(): int(value, 16) / pow(10, 18)
            for key, value in storage.items()
            if bet_funds_hex in key and next_bet_funds_hex not in key
        }
        return bet_funds
    else:
        raise HTTPException(status_code=storage.status_code, detail=f"There was an error retreiving the active bets!\n{storage.content}")


def get_all_rewards():
    sc = sc_gateway + "/address/" + SC_ADDRESS + "/keys"
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
        tx.data += "@" + Address(address).hex() + "@" + int_to_hex(int(str(multiplier).replace(".", "")))
    tx.gasLimit = (len(adds.keys()) + 1) * 6000000
    tx.version = config.get_tx_version()
    tx.sign(sender)
    sent_tx = tx.send(elrond_proxy)
    logger.info(f"Endgame rewards transaction:\t{sent_tx}")
    return sent_tx


async def confirm_transaction(txHash: str):
    endpoint = "https://devnet-api.elrond.com" + f"/transactions/{txHash}"
    while True:
        await asyncio.sleep(2)
        response = requests.get(endpoint)
        if response.status_code == 200:
            response = response.json()
            status = response["status"]
            if status == "success":
                return
        else:
            logger.debug(f"Bad request confirming endgame tx:\t{endpoint}")
