import requests
import random
from mcp.server.fastmcp import FastMCP

random_api_mcp = FastMCP(name="RandomAPIServer", stateless_http=True)

@random_api_mcp.tool()
def ping_random_api() -> str:
    """Ping a random API and return the results."""
    apis = [
        "https://jsonplaceholder.typicode.com/posts/1",
        "https://httpbin.org/json",
        "https://api.github.com/zen",
        "https://httpbin.org/uuid",
        "https://jsonplaceholder.typicode.com/users/1"
    ]
    
    selected_api = random.choice(apis)
    
    try:
        response = requests.get(selected_api, timeout=10)
        response.raise_for_status()
        
        return f"API: {selected_api}\\nStatus: {response.status_code}\\nResponse: {response.text[:500]}"
    except requests.exceptions.RequestException as e:
        return f"Error pinging {selected_api}: {str(e)}"

@random_api_mcp.tool()
def get_random_api_info() -> str:
    """Get information about a random API."""
    api_info = {
        "https://jsonplaceholder.typicode.com": "A free fake online REST API for testing and prototyping.",
        "https://httpbin.org": "A simple HTTP Request & Response Service.",
        "https://api.github.com": "The GitHub API provides access to GitHub's features programmatically."
    }
    
    selected_api = random.choice(list(api_info.keys()))
    description = api_info[selected_api]
    
    return f"API: {selected_api}\\nDescription: {description}"


if __name__ == "__main__":
    random_api_mcp.run()