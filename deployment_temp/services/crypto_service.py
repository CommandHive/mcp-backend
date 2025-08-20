from eth_account.messages import encode_defunct
from eth_account import Account


class CryptoService:
    @staticmethod
    def verify_signature(message: str, signature: str, wallet_address: str) -> bool:
        """
        Verify that a signature was created by the owner of the wallet address.
        
        Args:
            message: The original message that was signed
            signature: The signature to verify
            wallet_address: The expected wallet address of the signer
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            # Encode the message for Ethereum signing
            message_hash = encode_defunct(text=message)
            
            # Recover the address from the signature
            recovered_address = Account.recover_message(message_hash, signature=signature)
            
            # Compare addresses (case-insensitive)
            return recovered_address.lower() == wallet_address.lower()
            
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False

    @staticmethod
    def normalize_wallet_address(wallet_address: str) -> str:
        """Normalize wallet address to lowercase for consistent storage."""
        return wallet_address.lower()

    @staticmethod
    def is_valid_ethereum_address(address: str) -> bool:
        """Check if a string is a valid Ethereum address format."""
        try:
            # Basic format check: starts with 0x and is 42 characters long
            if not address.startswith('0x') or len(address) != 42:
                return False
            
            # Check if it's a valid hex string
            int(address[2:], 16)
            return True
            
        except ValueError:
            return False


crypto_service = CryptoService()