#!/usr/bin/python3

import json
import requests
import time
import sys

BITCOIN_URL = "http://127.0.0.1:8332"
BITCOIN_USER = "TODO_REPLACE"
BITCOIN_PASS = "TODO_REPLACE"

def query_bitcoind(command, args):
    try:
        response = requests.post(BITCOIN_URL,
                             auth=(BITCOIN_USER, BITCOIN_PASS),
                             data=json.dumps({"method": command, "params": args, "jsonrpc": "2.0", "id": "0"}))
        response.raise_for_status()
        result = response.json()
        if "error" in result and result["error"] is not None:
            return None
        return result["result"]
    except requests.exceptions.RequestException:
        return None

def get_address_utxos(address):
    result = query_bitcoind("scantxoutset", ["start", [f"addr({address})"]])
    if result is None:
        address_info = query_bitcoind("getaddressinfo", [address])
        if address_info and 'scriptPubKey' in address_info:
            result = query_bitcoind("scantxoutset", ["start", [f"raw({address_info['scriptPubKey']})"]])
    return result.get('unspents', []) if result else []

def get_transaction_details(txid):
    return query_bitcoind("getrawtransaction", [txid, True])

def monitor_wallet(address):
    print(f"Monitoring wallet address: {address}")
    last_utxos = set()

    while True:
        try:
            current_utxos = set(json.dumps(utxo) for utxo in get_address_utxos(address))

            new_utxos = current_utxos - last_utxos
            removed_utxos = last_utxos - current_utxos

            if new_utxos:
                print(f"\nAlert! New incoming transaction(s) detected for {address}:")
                for utxo_json in new_utxos:
                    utxo = json.loads(utxo_json)
                    print(f"Transaction ID: {utxo['txid']}")
                    print(f"Amount received: {utxo['amount']} BTC")
                    print("---")

            if removed_utxos:
                print(f"\nAlert! Outgoing transaction(s) detected for {address}:")
                for utxo_json in removed_utxos:
                    utxo = json.loads(utxo_json)
                    tx_details = get_transaction_details(utxo['txid'])
                    if tx_details:
                        for vout in tx_details['vout']:
                            if address not in vout['scriptPubKey'].get('addresses', []):
                                print(f"Transaction ID: {utxo['txid']}")
                                print(f"Amount sent: {vout['value']} BTC")
                                print(f"To address: {vout['scriptPubKey'].get('addresses', ['Unknown'])[0]}")
                                print("---")

            last_utxos = current_utxos
            time.sleep(60)  # Check every 60 seconds

        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python watch-wallet.py <bitcoin_address>")
        sys.exit(1)

    wallet_address = sys.argv[1]
    monitor_wallet(wallet_address)