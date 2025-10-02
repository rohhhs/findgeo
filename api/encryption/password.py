import hashlib
import secrets

from ..definitions import *

def encryptPassword(password: str) -> str:
    """
    Encrypts a password using PBKDF2 with SHA-256 hashing and a random salt.
    
    Args:
        password (str): The plain text password to encrypt
        
    Returns:
        str: The encrypted password in format "salt:hashed_password"
    """
    salt = secrets.token_hex(32)
    pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                  password.encode('utf-8'), 
                                  salt.encode('utf-8'), 
                                  100000)
    return f"{salt}:{pwdhash.hex()}"

def verifyPassword(stored_password: str, provided_password: str) -> bool:
    """
    Verifies a provided password against the stored encrypted password.
    
    Args:
        stored_password (str): The stored encrypted password in format "salt:hashed_password"
        provided_password (str): The plain text password to verify
        
    Returns:
        bool: True if password matches, False otherwise
    """
    salt, stored_hash = stored_password.split(':')
    pwdhash = hashlib.pbkdf2_hmac('sha256',
                                  provided_password.encode('utf-8'),
                                  salt.encode('utf-8'),
                                  100000)
    return pwdhash.hex() == stored_hash

def saveUser(username: str, encrypted_password: str, filepath: str = 'users.txt'):
    """
    Saves username and encrypted password to a file.
    
    Args:
        username (str): The username
        encrypted_password (str): The encrypted password
        filepath (str): Path to the file where data will be stored
    """
    print (filepath)
    with open(filepath, 'a') as f:
        f.write(f"{username}\t\t\t{encrypted_password}\n")

def findUser(username: str, filepath: str = 'users.txt') -> str:
    """
    Finds and returns the encrypted password for a given username.
    
    Args:
        username (str): The username to search for
        filepath (str): Path to the file containing user data
        
    Returns:
        str: The encrypted password if found, None otherwise
    """
    try:
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split('\t\t\t')
                if len(parts) == 2 and parts[0] == username:
                    return parts[1]
    except FileNotFoundError:
        pass
    return None