# blockchain/deploy.py
import os, json, time, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from web3 import Web3
from solcx import compile_source, install_solc
from config import GANACHE_URL, DEPLOYED_PATH, SENSOR_NODES
from blockchain.blockchain_writer import CONTRACT_SRC


def main():
    if os.path.exists(DEPLOYED_PATH):
        print("[Deploy] Already deployed. Delete deployed_addresses.json to redeploy.")
        return

    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    for i in range(15):
        if w3.is_connected():
            break
        print(f"[Deploy] Waiting for Ganache ({i+1}/15)...")
        time.sleep(2)
    else:
        raise RuntimeError("Ganache not reachable")

    deployer = w3.eth.accounts[0]
    print(f"[Deploy] Deployer: {deployer}")

    install_solc("0.8.19")
    compiled = compile_source(CONTRACT_SRC, solc_version="0.8.19",
                               output_values=["abi", "bin"])
    key      = "<stdin>:AudioLedger"
    abi      = compiled[key]["abi"]
    bytecode = compiled[key]["bin"]

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash  = contract.constructor().transact({"from": deployer, "gas": 3000000})
    receipt  = w3.eth.wait_for_transaction_receipt(tx_hash)
    address  = receipt.contractAddress
    print(f"[Deploy] AudioLedger at {address}")

    # Register all 3 sensor nodes
    deployed_contract = w3.eth.contract(address=address, abi=abi)
    for name, cfg in SENSOR_NODES.items():
        deployed_contract.functions.registerNode(cfg["node_id"]).transact(
            {"from": deployer, "gas": 100000})
        print(f"[Deploy] Registered node: {cfg['node_id']} ({name})")

    os.makedirs(os.path.dirname(DEPLOYED_PATH) or ".", exist_ok=True)
    with open(DEPLOYED_PATH, "w") as f:
        json.dump({"AudioLedger": {"address": address, "abi": abi},
                   "deployer": deployer}, f, indent=2)
    print(f"[Deploy] Saved to {DEPLOYED_PATH}")


if __name__ == "__main__":
    main()
