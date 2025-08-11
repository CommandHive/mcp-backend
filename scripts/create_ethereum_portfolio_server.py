#!/usr/bin/env python3
"""
Create a minimal MCP server record that gets Ethereum portfolio data.
Usage:
    python scripts/create_ethereum_portfolio_server.py

It inserts a new row into the `servers` table with source code that defines
an MCP server instance and exposes a `get_ethereum_portfolio` tool.
"""

import uuid
from datetime import datetime
from services.supabase_client import supabase_client

# MCP server code that gets Ethereum portfolio for an address
SERVER_CODE = '''
import requests
import json

ethereum_portfolio_mcp = FastMCP(name="EthereumPortfolioServer", stateless_http=True)

@ethereum_portfolio_mcp.tool()
def get_ethereum_portfolio(address: str) -> str:
    """Get portfolio information for an Ethereum address."""
    if not address or len(address) != 42 or not address.startswith('0x'):
        return "Error: Invalid Ethereum address format. Address should be 42 characters starting with 0x"
    
    try:
        # Using Etherscan API (free tier) to get balance
        etherscan_url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest&apikey=YourApiKeyToken"
        
        response = requests.get(etherscan_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == '1':
            balance_wei = int(data['result'])
            balance_eth = balance_wei / 1e18
            
            portfolio_info = {
                "address": address,
                "eth_balance": f"{balance_eth:.6f} ETH",
                "balance_wei": str(balance_wei),
                "note": "Using free Etherscan API - for production use, add proper API key and token balance queries"
            }
            
            return json.dumps(portfolio_info, indent=2)
        else:
            return f"Error from Etherscan API: {data.get('message', 'Unknown error')}"
            
    except requests.exceptions.RequestException as e:
        return f"Error fetching portfolio data: {str(e)}"
    except Exception as e:
        return f"Error processing portfolio data: {str(e)}"
'''


def main() -> None:
    server_id = str(uuid.uuid4())
    now = datetime.now()

    insert_query = """
        INSERT INTO servers (
            id, user_id, name, slug, description, version,
            status, visibility, source_code, created_at, updated_at, category
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        )
    """

    values = (
        server_id,
        "ab850c4a-d376-4d53-bf35-ff2d2ea2e191",
        "Ethereum Portfolio Server",
        "ethereum-portfolio",
        "Server that gets portfolio information for Ethereum addresses",
        "1.0.0",
        "active",
        "public",
        SERVER_CODE,
        now,
        now,
        "blockchain",
    )

    supabase_client.execute_query(insert_query, values)
    print(f"✅ Created Ethereum Portfolio Server. id={server_id} slug=ethereum-portfolio")
    print("You can set this environment variable to wire it into tests:")
    print(f"  export ETHEREUM_PORTFOLIO_SERVER_ID={server_id}")


if __name__ == "__main__":
    main()