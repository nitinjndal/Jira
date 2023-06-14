#! /usr/bin/env python
#
# %%

import os,stat
import argparse
import json
import re
# %%
from cryptography.fernet import Fernet

def generate_key():
    """
    Generates a key and save it into a file
    """
    key_path=os.path.dirname(__file__) + "/enc.key"
    key = Fernet.generate_key()
    with open(key_path, "wb") as key_file:
        key_file.write(key)

def load_key():
    """
    Load the previously generated key
    """
    key_path=os.path.dirname(__file__) + "/enc.key"
    # if not os.path.exists(key_path):
    #     generate_key() # execute only once
    return open(key_path, "rb").read()


def encrypt_message(message):
    """
    Encrypts a message
    """

    key = load_key()
    encoded_message = message.encode()
    f = Fernet(key)
    encrypted_message = f.encrypt(encoded_message)

    return encrypted_message

def encrypt_file(filename):
    """
    Encrypts a message
    """
    with open(filename,"r") as f:
        message=f.read()
    message=encrypt_message(message)
    with open(filename,"wb") as f:
        f.write(message)


def decrypt_message(encrypted_message):
    """
    Decrypts an encrypted message
    """
    key = load_key()
    f = Fernet(key)
    encoded_message = encrypted_message.encode()
    decrypted_message = f.decrypt(encoded_message)

    return decrypted_message


def decrypt_file(filename):
    """
    Decrypts an encrypted message
    """
    with open(filename,"r") as f:
        message=f.read()
    message = decrypt_message(message)
    with open(filename,"wb") as f:
        f.write(message)



#%%


def read_credentials_File(filename):
    creds=None
    filename=os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))
    mode = os.stat(filename).st_mode

    if  (mode & stat.S_IRGRP) or (mode & stat.S_IROTH) or (mode & stat.S_IWGRP) or (mode & stat.S_IWOTH):
        print(filename + ' readable by group or other people. Please revoke access of others of file using command\n chmod 600 ' + filename)
        exit()


    with open(filename,"r") as f:
        creds=f.read()
        creds=decrypt_message(creds)
        creds = json.loads(creds)
    return creds

def write_credentials_File(filename,jsondata):
    string=json.dumps(jsondata)
    string=encrypt_message(string)
    with open(filename,"wb") as f:
        f.write(string)
    os.chmod(filename,stat.S_IRWXU)


# %%


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="EncryptFile")
    argparser.add_argument('filename', nargs='+')

    args = argparser.parse_args()
    # print(args)
    if len(args.filename) != 1 :
        print("Error , give one file to decrypt")
    #decrypt_file(args.filename[0])

    encrypt_file(args.filename[0])