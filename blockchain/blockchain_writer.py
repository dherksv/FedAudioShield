# blockchain/blockchain_writer.py
import os, json
from web3 import Web3
from config import GANACHE_URL, DEPLOYED_PATH

CONTRACT_SRC = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract AudioLedger {
    struct AudioEvent {
        uint256 timestamp;
        string  nodeId;
        string  fingerprint;    // SHA-256(MFCC + node_id + ts) — no raw audio
        string  keyword;
        string  emotion;
        uint256 ifScore;        // ×1000
        string  alertLevel;
    }
    AudioEvent[] public events;
    mapping(string => bool) public registeredNodes;
    address public owner;

    event EventLogged(uint256 indexed idx, string nodeId, string alertLevel);
    event NodeRegistered(string nodeId);

    constructor() { owner = msg.sender; }

    modifier onlyOwner() { require(msg.sender == owner, "Not owner"); _; }

    function registerNode(string memory nodeId) external onlyOwner {
        registeredNodes[nodeId] = true;
        emit NodeRegistered(nodeId);
    }

    function verifyNode(string memory nodeId) external view returns (bool) {
        return registeredNodes[nodeId];
    }

    function logEvent(string memory nodeId, string memory fingerprint,
                      string memory keyword, string memory emotion,
                      uint256 ifScore, string memory alertLevel) external {
        events.push(AudioEvent(block.timestamp, nodeId, fingerprint,
                               keyword, emotion, ifScore, alertLevel));
        emit EventLogged(events.length - 1, nodeId, alertLevel);
    }

    function getEventCount() external view returns (uint256) { return events.length; }
}
"""


class BlockchainWriter:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
        if not self.w3.is_connected():
            print(f"[Blockchain] WARNING: Cannot connect to {GANACHE_URL}")
            self._connected = False
            return
        self._connected = True
        self.account = self.w3.eth.accounts[0]

        try:
            with open(DEPLOYED_PATH) as f:
                deployed = json.load(f)
            self.contract = self.w3.eth.contract(
                address=deployed["AudioLedger"]["address"],
                abi=deployed["AudioLedger"]["abi"],
            )
            print("[Blockchain] Connected to AudioLedger contract")
        except FileNotFoundError:
            print(f"[Blockchain] No deployed contract found at {DEPLOYED_PATH}")
            print("[Blockchain] Run: python blockchain/deploy.py")
            self.contract = None

    def verify_node(self, node_id: str) -> bool:
        if not self._connected or not self.contract:
            return True   # fail-open in dev mode
        try:
            return self.contract.functions.verifyNode(node_id).call()
        except Exception:
            return True

    def write_audio_block(self, data: dict) -> dict:
        if not self._connected or not self.contract:
            return {"hash": "0x0", "block": -1}
        try:
            tx = self.contract.functions.logEvent(
                str(data.get("node_id", "")),
                str(data.get("fingerprint", "")),
                str(data.get("keyword", "")),
                str(data.get("emotion", "")),
                int(float(data.get("if_score", 0)) * 1000),
                str(data.get("alert_level", "NORMAL")),
            ).transact({"from": self.account, "gas": 300000})
            receipt = self.w3.eth.wait_for_transaction_receipt(tx)
            return {
                "hash":  receipt.transactionHash.hex(),
                "block": receipt.blockNumber,
            }
        except Exception as e:
            print(f"[Blockchain] Write error: {e}")
            return {"hash": "", "block": -1}
