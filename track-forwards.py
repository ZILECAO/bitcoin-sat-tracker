#!/usr/bin/python3

import json, os.path, requests, string, sys, time

BITCOIN_URL = "http://127.0.0.1:8332"
BITCOIN_USER = "TODO_REPLACE"  # RPC username from bitcoin.conf
BITCOIN_PASS = "TODO_REPLACE"  # RPC password from bitcoin.conf

def spending_txid(txid, vout):
    response = requests.get(f"https://mempool.space/api/tx/{txid}/outspend/{vout}").json()
    if response['spent']: return response["txid"]
    return None

def block_reward(height):
    halvings = height // 210000
    reward = 5000000000
    while halvings > 0:
        reward //= 2
        halvings -= 1
    return reward

def query_bitcoind(command, args):
    return requests.post(BITCOIN_URL,
                         auth=(BITCOIN_USER, BITCOIN_PASS),
                         data=json.dumps({"method": command, "params": args, "jsonrpc": "2.0", "id": "0"})).json()["result"]

def get_raw_transaction(txid):
    if txid == "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b":
        sys.stderr.write("The genesis block coinbase is not considered an ordinary transaction and cannot be retrieved\n")
        sys.exit(1)
    tx = query_bitcoind("getrawtransaction", [txid, True])
    if not tx:
        sys.stderr.write(f"tx {txid} not found\n")
        sys.exit(1)
    if "blockhash" not in tx:
        sys.stderr.write(f"tx {txid} not confirmed\n")
        sys.exit(1)
    return tx

def get_block(block_hash):
    return query_bitcoind("getblock", [block_hash])

def get_fee_for_txid_from_bitcoind(txid, count, total):
    raw = get_raw_transaction(txid)
    return (sum(int(round(get_raw_transaction(input["txid"])["vout"][input["vout"]]["value"] * 1e8)) for input in raw["vin"]) -
            sum(int(round(output["value"]*1e8)) for output in raw["vout"]))

def track_satpoint(satpoint):
    hop = 0
    print("\n" + "="*80)
    print(f"TRACKING SATPOINT: {satpoint}")
    print("="*80)
    while True:
        # we break down the old satpoint into 3 parts
        (txid, vout, offset) = satpoint.split(":")
        vout = int(vout)
        offset = int(offset)
        output = f"{txid}:{vout}"
        raw_tx = get_raw_transaction(txid)
        if vout >= len(raw_tx['vout']):
            sys.stderr.write(f"tx {txid} has {len(raw_tx['vout'])} outputs numbered 0 to {len(raw_tx['vout']) - 1}; it has no output number {vout}\n")
            sys.exit(1)
        block = get_block(raw_tx["blockhash"])
        blocktime = block["time"]
        height = block["height"]
        scriptPubKey = raw_tx['vout'][vout]['scriptPubKey']
        address = scriptPubKey.get('address', scriptPubKey['type'])
        
        print(f"{hop:4d} - {height:6d} - {time.ctime(blocktime)} - {satpoint} - {address}")
        
        new_txid = spending_txid(txid, vout)
        if not new_txid:
            print("-"*80)
            print("FINAL DESTINATION REACHED")
            print(f"Final Address: {address}")
            print("-"*80)
            return address

        raw_tx = get_raw_transaction(new_txid)
        for input in raw_tx["vin"]:
            prev_txid = input["txid"]
            prev_vout = input["vout"]
            if f"{prev_txid}:{prev_vout}" == output:
                break

            # look up the value of each input
            prev_tx = get_raw_transaction(prev_txid)
            offset += int(round(prev_tx["vout"][prev_vout]["value"] * 1e8))

        vout = 0
        found = False
        for output in raw_tx["vout"]:
            value = int(round(output["value"] * 1e8))
            if value > offset:
                found = True
                break
            offset -= value
            vout += 1

        if not found:
            block = get_block(raw_tx["blockhash"])
            txs = block["tx"]
            height = block["height"]
            subsidy = block_reward(height)
            our_tx = next(i for i, tx in enumerate(txs) if tx == new_txid)
            print(f"[ output spent as fee - counting up {our_tx} fees ]")
            coinbase_tx = txs[0]
            fee_txs = txs[1:our_tx + 1]
            fees = sum(get_fee_for_txid_from_bitcoind(txid, i+1, our_tx) for i, txid in enumerate(fee_txs))
            offset = subsidy + fees + offset
            new_txid = coinbase_tx

            vout = 0
            found = False
            for output in get_raw_transaction(new_txid)["vout"]:
                value = int(round(output["value"] * 1e8))
                if value > offset:
                    found = True
                    break
                offset -= value
                vout += 1

            if not found:
                print(f"offset {offset} into non-existent coinbase output {new_txid}:{vout}")
                sys.exit(1)

        satpoint = f"{new_txid}:{vout}:{offset}"
        hop += 1

def main():
    # Sys.argv should have 3 arguments and looks something like this: 
    # python3 track-forwards.py 5435a6f76793a55e20626fb3fda796e93462f62ccb0f244c382127043f495451:0
    # The sys.argv[1] is the txid:vout of the output we want to track backwards
    # The sys.argv[2] is the offset amount we want to start tracking from

    if len(sys.argv) != 2:
        print("Usage: python3 track-forwards.py <txid:vout>")
        sys.exit(1)

    tx_output = sys.argv[1]
    (txid, vout) = tx_output.split(":")
    raw_tx = get_raw_transaction(txid)
    vout = int(vout)
    value = int(round(raw_tx["vout"][vout]["value"] * 1e8))

    # Here, we scan the satoshis within the output in increments. 
    # The idea here is that satoshis in the original output may have been divided up and sent to multiple addresses. We want to track all of them.
    # The interval is dynamically calculated to always have 25 queries.
    interval = (value + 24) // 25  # Round up to ensure we cover all sats

    print("\n" + "="*80)
    print(f"INITIAL VALUE: {value} sats")
    print(f"INTERVAL: {interval} sats")
    print("="*80 + "\n")

    count = 0
    found_destinations = []

    for offset in range(0, value, interval):
        end_offset = min(offset + interval - 1, value - 1)
        print(f"\nTRACKING SAT RANGE: {offset}-{end_offset}")
        print("-"*80)
        
        satpoint = f"{tx_output}:{offset}"
        final_destination = track_satpoint(satpoint)
        
        found_destinations.append(f"Sat range {offset}-{end_offset} final destination: {final_destination}")
        count += 1

    print("\n" + "="*80)
    print("PROGRAM MAIN() END")
    print(f"Total sat ranges tracked: {count}")
    print("="*80 + "\n")

    print("SUMMARY OF FINAL DESTINATIONS:")
    print("-"*80)
    for dest in found_destinations:
        print(dest)
    print("-"*80)

if __name__ == "__main__":
    main()
