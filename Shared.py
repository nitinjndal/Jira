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

import collections
import itertools
import Encrypt
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
def DebugMsg(msg1,msg2="",printmsg=True,ForcePrint=False,print_dt=True,error=False):
    if error:
        print("ERROR: " ,end=": " )
        if Logging.ConsoleLogFile is not None:
            Logging.ConsoleLogFile.write("ERROR: ")

    if (Logging.debug or ForcePrint) and printmsg:
        if not (((str(msg1) == "" )or (msg1 is None)) and ((str(msg2) == "") or (msg2 is None))) :
            if print_dt:
                print(dt.datetime.now().strftime("%c"),end=": " )
                if Logging.ConsoleLogFile is not None:
                    Logging.ConsoleLogFile.write(dt.datetime.now().strftime("%c") + ": ")
        print(str(msg1).encode('utf-8',errors='ignore').decode('charmap',errors='ignore'),end=" " )
        if Logging.ConsoleLogFile is not None:
            Logging.ConsoleLogFile.write(str(msg1).encode('utf-8',errors='ignore').decode('charmap',errors='ignore') + " ")
        if msg2 is not None:
            print(str(msg2).encode('utf-8',errors='ignore').decode('charmap',errors='ignore'))
            if Logging.ConsoleLogFile is not None:
                Logging.ConsoleLogFile.write(str(msg2).encode('utf-8',errors='ignore').decode('charmap',errors='ignore') + "\n")
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

def Error(msg1,msg2=None,printmsg=True,ForcePrint=False,print_dt=True):
    DebugMsg(msg1,msg2,printmsg,True,print_dt,error=True)

class Shared:
    defaultsFilePath=os.path.dirname(os.path.abspath(__file__)) + "/defaults.json"


    def read_credentials_File(filename):
        filename=os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))
        try:
            with open(filename,"r") as f: 
                json.load(f)
            ## if loaded correctly
            print("Credential File is not encrypted. Please encrypt it with encryption tool")
            
        except:
            creds=None
            mode = os.stat(filename).st_mode

            if  (mode & stat.S_IRGRP) or (mode & stat.S_IROTH) or (mode & stat.S_IWGRP) or (mode & stat.S_IWOTH):
                print(filename + ' readable by group or other people. Please revoke access of others of file using command\n chmod 600 ' + filename)
                exit()
            creds=Encrypt.read_credentials_File(filename)
            return creds


    def update_credentials(filename,credentials):
        filename=os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))
        creds = Encrypt.write_credentials_File(filename,credentials) 
        return creds

    def read_credentials(filename,credentialsHead):
        filename=os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))
        creds = Shared.read_credentials_File(filename) 
        if creds is not None:
            if credentialsHead in creds: 
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
    
    def tail(filename, n=10):
        with open(filename) as f:
            return "\n".join(list(collections.deque(f, n)))

    def get_n_lines_after_before(pattern,filename,n=3,line_prefix="",line_suffix=""):
        lines=[]
        retval=""
        start_count=False
        count=n+1
        with open(filename) as f:
            if n > 0 :
                before = collections.deque(maxlen=n)
            for line in f:
                count+=1
                if re.search(pattern,line,flags=re.IGNORECASE) is not None:
                    if n > 0 and  count > n:
                        count=0
                        lines=lines+ list(before)
                    elif n==0:
                        lines.append(line)
#                    lines.append(line)
                if count < n:
                    lines.append(line)
                elif count == n:
                    lines.append("####################\n\n")
                if n > 0 :
                    before.append(line)
        for line in lines:
            retval=retval + line_prefix+  str(line).strip() + line_suffix + "\n"
        return retval
