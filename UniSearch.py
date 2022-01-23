#! /usr/bin/env python
#
import logging
import sys
import os
import re
import argparse
import json

# %%
import datetime as dt
import Jira
import SharepointSearch
import Confluence
import threading
# %%
## import shutil
#from sympy import primenu
## import pandas as pd
## import time
## import numpy as np
## import tarfile
## from difflib import SequenceMatcher
## import Common.local_functions as LF

debug=True

ConsoleLogFile = open("./console.log", "w")
def DebugMsg(msg1,msg2="",printmsg=True,ForcePrint=False):
    if (debug or ForcePrint) and printmsg:
        if not (((str(msg1) == "" )or (msg1 is None)) and ((str(msg2) == "") or (msg2 is None))) :
            print(dt.datetime.now().strftime("%c"),end=" " )
            ConsoleLogFile.write(dt.datetime.now().strftime("%c") + " ")
        print(msg1,end=" " )
        ConsoleLogFile.write(str(msg1) + " ")
        if msg2 is not None:
            print(msg2)
            ConsoleLogFile.write(str(msg2) + "\n")
        else:
            print("")
            ConsoleLogFile.write("\n")

        sys.stdout.flush()
        sys.stderr.flush()
        ConsoleLogFile.flush()

def DebugMsg2(msg1,msg2=None,printmsg=True):
    DebugMsg(msg1,msg2,printmsg)

def DebugMsg3(msg1,msg2=None,printmsg=True):
    DebugMsg(msg1,msg2,printmsg)

def Info(msg1,msg2=None,printmsg=True):
    DebugMsg(msg1,msg2,printmsg,ForcePrint=True)


class UniSearch:

    def __init__(self, keywords,regexs=[],commentedBy=[],appendInJquery="",appendInCquery="",customJquery=None,customCquery=None,getregexs=[]):

        credentialsFile= "~/.UniSearch.json"
        credentialsFile=os.path.abspath(os.path.expanduser(os.path.expandvars(credentialsFile)))

        JiraCloudThread = threading.Thread(target=Jira.Jira,
                              kwargs=dict(keywords=keywords,
                                          commentedBy=commentedBy,
                                          regexs=regexs,
                                          appendInJquery=appendInJquery,
                                          customJquery=customJquery,
                                          getregexs=getregexs,
                                          credentialsFile=credentialsFile))

        SharePointThread = threading.Thread(target=SharepointSearch.SharepointSearch,
                              kwargs=dict(keywords=keywords,
                                          credentialsFile=credentialsFile,
                                          SearchSharepoint=True,
                                          SearchFindit=False))

        FinditThread = threading.Thread(target=SharepointSearch.SharepointSearch,
                              kwargs=dict(keywords=keywords,
                                          credentialsFile=credentialsFile,
                                          SearchSharepoint=False,
                                          SearchFindit=True))



        JiraThread = threading.Thread(target=Jira.Jira,
                                      kwargs=dict(
                                          keywords=keywords,
                                          commentedBy=commentedBy,
                                          regexs=regexs,
                                          appendInJquery=appendInJquery,
                                          customJquery=customJquery,
                                          getregexs=getregexs,
                                          credentialsFile=credentialsFile,
                                          credentialsHead="JiraCredentials"))

        ConfluenceThread = threading.Thread(
            target=Confluence.Confluence,
            kwargs=dict(keywords=args.keywords,
                        commentedBy=commentedBy,
                        regexs=regexs,
                        appendInCquery=appendInCquery,
                        customCquery=customCquery,
                        getregexs=getregexs,
                        credentialsFile=credentialsFile))

        JiraThread.start()
        JiraCloudThread.start()
        SharePointThread.start()
        FinditThread.start()
        ConfluenceThread.start()






if __name__ == "__main__":

    argparser = argparse.ArgumentParser(description="Jira")
    argparser.add_argument('keywords', nargs='+')
    argparser.add_argument(
        "-regex", metavar="regex", required=False, help="DashboardDataDir",nargs='+', default=[])

    argparser.add_argument(
        "-getregex", metavar="regex", required=False, help="DashboardDataDir",nargs='+', default=[])

    argparser.add_argument(
        "-commentedBy", metavar="UserName",  default="", required=False,
        help="Find tickets which are commented by persons. Pass comma separated names in double quotes")

    argparser.add_argument(
        "-appendInJquery", metavar="commentedby fasnfjksngkj",  default="", required=False,
        help="Append this as part of jquery")

    argparser.add_argument(
        "-appendInCquery", metavar="commentedby fasnfjksngkj",  default="", required=False,
        help="Append this as part of jquery")

    argparser.add_argument(
        "-customJquery", metavar="text ~ nitin AND commentedBy fasnfjksngkj",  default="", required=False,
        help="Use this is the only jquery")

    argparser.add_argument(
        "-customCquery", metavar="text ~ nitin AND commentedBy fasnfjksngkj",  default="", required=False,
        help="Use this is the only cquery")

    argparser.add_argument(
        "-verbose", action='store_true', help="Enable detailed log")


    argparser.add_argument(
        "-debug", action='store_true', help="Enable Debugging mode")


    args = argparser.parse_args()
    # print(args)
    #    debug=args.debug
    commentedBy=list(filter(None,args.commentedBy.split(",")))
    ## used filter to remove empty contents from list
    UniSearch(
    keywords=args.keywords,
     commentedBy=commentedBy,
     regexs=args.regex,
     appendInJquery=args.appendInJquery,
     appendInCquery=args.appendInCquery,
     customJquery=args.customJquery,
     customCquery=args.customCquery,
     getregexs=args.getregex
     )


    ConsoleLogFile.close()
# %%
