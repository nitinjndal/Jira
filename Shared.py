#! /usr/bin/env python
#

import sys
import requests
import logging
import datetime as dt
import json
import os
import stat

from bs4 import BeautifulSoup
from markdown import markdown
import re
import html2text

## import shutil
#from sympy import primenu
## import pandas as pd
## import time
## import numpy as np
## import tarfile
## from difflib import SequenceMatcher
## import Common.local_functions as LF


class Logging:
    debug=False
    ConsoleLogFile=None
    

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
def DebugMsg(msg1,msg2="",printmsg=True,ForcePrint=False,print_dt=True):
    if (Logging.debug or ForcePrint) and printmsg:
        if not (((str(msg1) == "" )or (msg1 is None)) and ((str(msg2) == "") or (msg2 is None))) :
            if print_dt:
                print(dt.datetime.now().strftime("%c"),end=": " )
                if Logging.ConsoleLogFile is not None:
                    Logging.ConsoleLogFile.write(dt.datetime.now().strftime("%c") + ": ")
        print(msg1.encode('utf-8',errors='ignore').decode('charmap',errors='ignore'),end=" " )
        if Logging.ConsoleLogFile is not None:
            Logging.ConsoleLogFile.write(msg1.encode('utf-8',errors='ignore').decode('charmap',errors='ignore') + " ")
        if msg2 is not None:
            print(msg2.encode('utf-8',errors='ignore').decode('charmap',errors='ignore'))
            if Logging.ConsoleLogFile is not None:
                Logging.ConsoleLogFile.write(msg2.encode('utf-8',errors='ignore').decode('charmap',errors='ignore') + "\n")
        else:
            print("")
            if Logging.ConsoleLogFile is not None:
                Logging.ConsoleLogFile.write("\n")

        sys.stdout.flush()
        if Logging.ConsoleLogFile is not None:
            Logging.ConsoleLogFile.flush()

def DebugMsg2(msg1,msg2=None,printmsg=True,ForcePrint=False,print_dt=True):
    DebugMsg(msg1,msg2,printmsg,ForcePrint,print_dt)

def DebugMsg3(msg1,msg2=None,printmsg=True,ForcePrint=False,print_dt=True):
    DebugMsg(msg1,msg2,printmsg,ForcePrint,print_dt)

def Info(msg1,msg2=None,printmsg=True,ForcePrint=False,print_dt=True):
    DebugMsg(msg1,msg2,printmsg,True,print_dt)

class Shared:
    defaultsFilePath=os.path.dirname(os.path.abspath(__file__)) + "/defaults.json"
    def read_credentials(filename,credentialsHead):
        creds=None
        filename=os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))
        mode = os.stat(filename).st_mode

        if  (mode & stat.S_IRGRP) or (mode & stat.S_IROTH) or (mode & stat.S_IWGRP) or (mode & stat.S_IWOTH):
            print(filename + ' readable by group or other people. Please revoke access of others of file using command\n chmod 644 ' + filename)
            exit()


        with open(filename) as f:
            creds = json.load(f)
            creds=creds[credentialsHead]['credentials']
        return creds

    def read_defaults(filename,credentialsHead):
        defaults=None
        filename=os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))
        with open(filename) as f:
            defaults= json.load(f)
            defaults = defaults[credentialsHead]
        return defaults

    def abs_path(filename):
        return os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))

    def isVpnConnected(server):
        rep=requests.get(server)
        if b"Sign in to your account" in rep.content:
            Info("Could not connect to " + server + ". Looks like VPN is not connected. Please connect to VPN and retry")
            return False
        return True
    
    def html_to_plain_text(html_string):
        markdown_string=html2text.html2text(html_string)
        #""" Converts a markdown string to plaintext """

        # md -> html -> text since BeautifulSoup can extract text cleanly
        html = markdown(markdown_string)

        # remove code snippets
        html = re.sub(r'<pre>(.*?)</pre>', ' ', html)
        html = re.sub(r'<code>(.*?)</code >', ' ', html)

        # extract text
        soup = BeautifulSoup(html, "html.parser")
        text = ''.join(soup.findAll(text=True))

        return text