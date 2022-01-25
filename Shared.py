#! /usr/bin/env python
#

import sys
import requests
import logging
import datetime as dt

## import shutil
#from sympy import primenu
## import pandas as pd
## import time
## import numpy as np
## import tarfile
## from difflib import SequenceMatcher
## import Common.local_functions as LF

def isVpnConnected(server):
    rep=requests.get(server)
    if b"Sign in to your account" in rep.content:
        Info("Could not connect to " + server + ". Looks like VPN is not connected. Please connect to VPN and retry")
        return False
    return True

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
        print(msg1,end=" " )
        if Logging.ConsoleLogFile is not None:
            Logging.ConsoleLogFile.write(str(msg1) + " ")
        if msg2 is not None:
            print(msg2)
            if Logging.ConsoleLogFile is not None:
                Logging.ConsoleLogFile.write(str(msg2) + "\n")
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
