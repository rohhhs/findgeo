import base64
import os

from .password import findUser
from ..definitions import *

def encodeAccount(username: str, encoded_password: str) -> str:
    """
    Creates a bearer token containing username and encrypted password.
    
    Args:
        username (str): The username
        encoded_password (str): The encrypted password
        
    Returns:
        str: Base64 encoded bearer token in format "username:encoded_password"
    """
    if not username or not encoded_password:
        return None
    token_data = f"{username}:{encoded_password}"
    return base64.b64encode(token_data.encode()).decode()

def decodeAccount(token: str) -> str:
    """
    Decodes a bearer token to extract username.
    
    Args:
        token (str): The base64 encoded bearer token
        
    Returns:
        str: The username from the token, or None if decoding fails
    """
    try:
        if not token:
            return None
        token_data = base64.b64decode(token.encode()).decode()
        parts = token_data.split(':', 1)
        if len(parts) != 2:
            return None
        username, encoded_password = parts
        if not username or not encoded_password:
            return None
        return username
    except (base64.binascii.Error, UnicodeDecodeError):
        return None

def checkToken(token: str) -> bool:
    username = decodeAccount(token)
    if username is None:
        return False
    return findUser(username, os.path.join(ASSET_DATA_ENCRYPTION_DIR, "users.txt")) is not None