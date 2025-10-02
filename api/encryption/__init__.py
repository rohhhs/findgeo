import os
import time

from ..definitions import *
from .password import findUser , saveUser , verifyPassword , encryptPassword
from .token import encodeAccount , decodeAccount , checkToken

start_time = time.time()

import hashlib
import secrets

def timeLine(point_number, description):
    """Log timeline point with exact time from start"""
    elapsed_time = time.time() - start_time
    print(f"[{elapsed_time:.3f}s] Timeline point {point_number}: {description}")

if __name__ == "__main__":
    timeLine(0, "Script started")
    # Setting code sample  
    password = "mySecretPassword123015"
    username = "john_doe2"
    token = 'am9obl9kb2UyOjk0MTY3ZDdhMGVlZTM4NTA4Y2ZhZWRhYTY0NzYxZTg3MTFlMTMwNmMzZGI1Nzc4NjAyZjY5OGYxZGZhNGJkNTE6M2JjMjQyYjA3YjlkODQxNzU3NjlhMWIzOTM0YTc2ZWU0ZGI4NGM1OThiMWQyNTI5NDY3MzRjNzZiYTljYTRmOQ=='
    # End of settign code sample 

    if (token == ''):
        encrypted = encryptPassword(password)
        timeLine(1, f"Password encrypted . {encrypted}")

        os.makedirs(ASSET_DATA_ENCRYPTION_DIR, exist_ok=True)
        if (findUser(username , os.path.join(ASSET_DATA_ENCRYPTION_DIR , 'users.txt'))):
            timeLine(2.0, "Username Found . ")
        else:
            saveUser(username, encrypted , os.path.join(ASSET_DATA_ENCRYPTION_DIR , 'users.txt'))
            timeLine(2.1, "Username created . ")

        # Retrieve and verify password
        stored_password = findUser(username , os.path.join(ASSET_DATA_ENCRYPTION_DIR , 'users.txt'))
        if stored_password and verifyPassword(stored_password, password):
            timeLine(3.0, "Account verified . ")
            token = encodeAccount(username , encrypted)
            timeLine(3.0, f"Account verified . Token generated : {token} ")
        else:
            timeLine(3.1, "ERROR . Invalid password ! ")
    else :
        username = decodeAccount(token)
        if (findUser(username , os.path.join(ASSET_DATA_ENCRYPTION_DIR , 'users.txt'))):
            timeLine(4.0, "Token decoded , username found . ")
        else :
            timeLine(4.1, "ERROR . Token decoded , username not found ! ")

    print (checkToken(token))