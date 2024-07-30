Python scripts to index Bitcoin transactions. Need to be run on a server with Bitcoin Core installed. 

## Quickstart
1. Install a Bitcoin Core node on an AWS EC2 instance. Ensure that the node is synced to the latest block with:
```
bitcoin-cli getblockchaininfo
```
note: syncing blocks will take a few days, and if you need any guidance on setting up a btc node, this guide is a good start: https://medium.com/@daniel.wegmann/step-by-step-guide-to-run-bitcoin-core-node-on-aws-3761174a861a

2. Add the python scripts in this repo to the same directory as your .bitcoin folder. Create a new folder and paste in the code with
```
nano track-forwards.py
nano watch-wallet.py
```
3. Set up a bitcoin.conf file within your .bitcoin folder with the following:
```
# Accept command line and JSON-RPC commands
server=1

daemon=1

# Username for JSON-RPC connections
rpcuser=TODO_REPLACE
# Password for JSON-RPC connections
rpcpassword=TODO_REPLACE
# Allow JSON-RPC connections from, by default only localhost are allowed
rpcallowip=127.0.0.1
# Maintain a full transaction index, used by the getrawtransaction rpc call (defaul>
txindex=1
```

4. Replace Bitcoin configuration Username and Password tagged "TODO_REPLACE" for RPC connections with your own.

5. Run the example scripts
```
python3 track-forwards.py 5435a6f76793a55e20626fb3fda796e93462f62ccb0f244c382127043f495451:0
python3 watch-wallet.py <insert_wallet_address_here>
```

