#!/usr/bin/env python3
"""
Blockchain client to interact with MCPToolCallLogLite smart contract on Sei testnet.
"""

import os
from web3 import Web3
import time
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Contract configuration from environment variables
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x5C04Bd7EC9AF8c3e67a49A75970F0b6D5EA01BA9")
SEI_TESTNET_RPC = os.getenv("SEI_TESTNET_RPC", "https://evm-rpc-testnet.sei-apis.com")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "b35e7b6dbffe31be37832bfc130cbc3de87ad6690e2b197991a9366201893888")
CHAIN_ID = int(os.getenv("CHAIN_ID", "1328"))
GAS_PRICE = int(os.getenv("GAS_PRICE", "20000000000"))

# Contract ABI - only the functions we need
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "mcpId", "type": "string"},
            {"internalType": "uint64", "name": "timestamp", "type": "uint64"},
            {"internalType": "string", "name": "clientInfo", "type": "string"},
            {"internalType": "string", "name": "toolCallName", "type": "string"}
        ],
        "name": "registerCall",
        "outputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalCalls",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "mcpId", "type": "string"}],
        "name": "getMcpCallCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "id", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "submitter", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "mcpId", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "mcpCallCount", "type": "uint256"},
            {"indexed": False, "internalType": "uint64", "name": "timestamp", "type": "uint64"},
            {"indexed": False, "internalType": "string", "name": "clientInfo", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "toolCallName", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "blockTimestamp", "type": "uint256"}
        ],
        "name": "ToolCall",
        "type": "event"
    }
]

class MCPContractClient:
    def __init__(self):
        try:
            # Connect to Sei testnet
            self.w3 = Web3(Web3.HTTPProvider(SEI_TESTNET_RPC))
            
            # Verify connection
            if not self.w3.is_connected():
                raise Exception("Failed to connect to Sei testnet")
            
            # Set up account
            self.account = self.w3.eth.account.from_key(PRIVATE_KEY)
            self.w3.eth.default_account = self.account.address
            
            # Create contract instance
            self.contract = self.w3.eth.contract(
                address=CONTRACT_ADDRESS,
                abi=CONTRACT_ABI
            )
            
            print(f"🔗 Connected to Sei testnet")
            print(f"📧 Using account: {self.account.address}")
            print(f"📋 Contract address: {CONTRACT_ADDRESS}")
            
        except Exception as e:
            print(f"❌ Failed to initialize blockchain client: {e}")
            self.w3 = None
            self.contract = None

    def register_tool_call(self, mcp_id: str, client_info: str, tool_call_name: str) -> Dict[str, Any]:
        """
        Register a new tool call in the smart contract.
        
        Args:
            mcp_id: Unique identifier for the MCP
            client_info: Information about the client making the call
            tool_call_name: Name of the tool being called
            
        Returns:
            Dictionary containing transaction details
        """
        if not self.w3 or not self.contract:
            return {'error': 'Blockchain client not initialized', 'status': 'failed'}
            
        try:
            # Get current timestamp
            timestamp = int(time.time())
            
            # Build transaction
            transaction = self.contract.functions.registerCall(
                mcp_id,
                timestamp,
                client_info,
                tool_call_name
            ).build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': GAS_PRICE,
                'nonce': self.w3.eth.get_transaction_count(self.account.address)
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, PRIVATE_KEY)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            # Wait for confirmation
            print(f"📝 Transaction sent: {tx_hash.hex()}")
            print("⏳ Waiting for confirmation...")
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Parse event logs
            tool_call_events = self.contract.events.ToolCall().process_receipt(receipt)
            
            result = {
                'transaction_hash': tx_hash.hex(),
                'block_number': receipt.blockNumber,
                'gas_used': receipt.gasUsed,
                'status': 'success' if receipt.status == 1 else 'failed'
            }
            
            if tool_call_events:
                event = tool_call_events[0]['args']
                result.update({
                    'call_id': event.id,
                    'mcp_call_count': event.mcpCallCount,
                    'submitter': event.submitter,
                    'block_timestamp': event.blockTimestamp
                })
                print(f"✅ Tool call registered with ID: {event.id}")
            
            return result
            
        except Exception as e:
            print(f"❌ Failed to register tool call: {e}")
            return {'error': str(e), 'status': 'failed'}

    def get_total_calls(self) -> int:
        """Get the total number of calls across all MCPs."""
        if not self.contract:
            return 0
        try:
            return self.contract.functions.totalCalls().call()
        except Exception as e:
            print(f"❌ Failed to get total calls: {e}")
            return 0

    def get_mcp_call_count(self, mcp_id: str) -> int:
        """Get the number of calls for a specific MCP ID."""
        if not self.contract:
            return 0
        try:
            return self.contract.functions.getMcpCallCount(mcp_id).call()
        except Exception as e:
            print(f"❌ Failed to get MCP call count: {e}")
            return 0

# Global instance
blockchain_client = MCPContractClient()

async def log_tool_call_to_blockchain(mcp_id: str, tool_call_name: str, client_info: str = "MCP Backend") -> Dict[str, Any]:
    """
    Async wrapper to log a tool call to the blockchain.
    
    Args:
        mcp_id: Unique identifier for the MCP server
        tool_call_name: Name of the tool being called
        client_info: Information about the client (optional)
        
    Returns:
        Dictionary containing the result of the blockchain transaction
    """
    print(f"🔗 Logging tool call to blockchain: {tool_call_name} for MCP {mcp_id}")
    
    result = blockchain_client.register_tool_call(mcp_id, client_info, tool_call_name)
    
    if result['status'] == 'success':
        print(f"✅ Successfully logged to blockchain!")
        print(f"   Call ID: {result.get('call_id', 'N/A')}")
        print(f"   Transaction: {result['transaction_hash']}")
        print(f"   Gas used: {result['gas_used']}")
    else:
        print(f"❌ Failed to log to blockchain: {result.get('error', 'Unknown error')}")
    
    return result