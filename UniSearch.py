#! /usr/bin/env python
#
from Shared import Logging, DebugMsg, Info, Error,Shared
Info("Started ")
import logging
import sys
import os
import re
import argparse
import json
import getpass 
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


class UniSearch:

    def __init__(self,
                 keywords,
                 regexs=[],
                 commentedBy=[],
                 appendInJquery="",
                 appendInCquery="",
                 customJquery=None,
                 customCquery=None,
                 getregexs=[]):

        begin_time = dt.datetime.now()
        defaultsFile = Shared.defaultsFilePath
        credentialsHead = "UniSearch"
        self.defaults = Shared.read_defaults(defaultsFile, credentialsHead)
        self.credentialsFile = Shared.abs_path(self.defaults["CredentialsFile"])
        if not os.path.exists(self.credentialsFile):
            username,unix_pw,confluence_token=self.inputCredentialsdummy()
            email=self.getEmail(username)
            Shared.CreateCredentialsFile(username,email,unix_pw,
                                         confluence_token,self.defaults,self.credentialsFile)

        creds= Shared.read_credentials_File(self.credentialsFile)

        if not Shared.validUnixCredentials(getpass.getuser(),creds['Jira']['credentials']['token']):
            username,unix_passw=self.getInputUnixCredentials()
            creds=Shared.updateCredentialsJson(unix_passw=unix_passw,jsondata=creds)
            Shared.update_credentials(self.credentialsFile,creds)

        if not Confluence.Confluence.isCredentialsValid(self.defaults['ConfluenceServer'],creds['Confluence']['credentials']['token']):
            confluence_token=self.getInputConfluenceToken()
            creds=Shared.updateCredentialsJson(conf_token=confluence_token,jsondata=creds)
            Shared.update_credentials(self.credentialsFile,creds)

        acquire_token_flow=SharepointSearch.SharepointSearch(credentialsFile=self.credentialsFile, keywords=[],SearchSharepoint=False,SearchFindit=False,SearchMail=False)
        acquire_token_flow.acquire_token(scope=["Sites.Read.All"])


        #	JiraCloudThread = threading.Thread(target=Jira.Jira,
        #					  kwargs=dict(keywords=keywords,
        #								  commentedBy=commentedBy,
        #								  regexs=regexs,
        #								  appendInJquery=appendInJquery,
        #								  customJquery=customJquery,
        #								  getregexs=getregexs,
        #								  credentialsFile=self.credentialsFile,
        #								  credentialsHead="JiraCloud"))

        SharePointThread = threading.Thread(
            target=SharepointSearch.SharepointSearch,
            kwargs=dict(keywords=keywords,
                        credentialsFile=self.credentialsFile,
                        regexs=regexs,
                        getregexs=getregexs,
                        SearchSharepoint=True,
                        SearchFindit=False,
                        SearchMail=False))

        FinditThread = threading.Thread(
            target=SharepointSearch.SharepointSearch,
            kwargs=dict(keywords=keywords,
                        credentialsFile=self.credentialsFile,
                        regexs=regexs,
                        getregexs=getregexs,
                        SearchSharepoint=False,
                        SearchFindit=True,
                        SearchMail=False))

        MailThread = threading.Thread(target=SharepointSearch.SharepointSearch,
                                      kwargs=dict(
                                          keywords=keywords,
                                          credentialsFile=self.credentialsFile,
                                          regexs=regexs,
                                          getregexs=getregexs,
                                          SearchSharepoint=False,
                                          SearchFindit=False,
                                          SearchMail=True))

        JiraThread = threading.Thread(target=Jira.Jira,
                                      kwargs=dict(
                                          keywords=keywords,
                                          commentedBy=commentedBy,
                                          regexs=regexs,
                                          getregexs=getregexs,
                                          appendInJquery=appendInJquery,
                                          customJquery=customJquery,
                                          credentialsFile=self.credentialsFile,
                                          credentialsHead="Jira"))

        ConfluenceThread = threading.Thread(
            target=Confluence.Confluence,
            kwargs=dict(keywords=args.keywords,
                        regexs=regexs,
                        appendInCquery=appendInCquery,
                        customCquery=customCquery,
                        getregexs=getregexs,
                        credentialsFile=self.credentialsFile))

        JiraThread.start()
        #	JiraCloudThread.start()
        SharePointThread.start()
        FinditThread.start()
        ConfluenceThread.start()
        MailThread.start()


        JiraThread.join()
        #	JiraCloudThread.join()
        SharePointThread.join()
        FinditThread.join()
        ConfluenceThread.join()
        MailThread.join()
        time_taken=dt.datetime.now() - begin_time
        time_taken = time_taken - dt.timedelta(microseconds=time_taken.microseconds)
        print("Completed. Time Taken : %d seconds" % time_taken.total_seconds()) 
    
    def getInputUnixCredentials(self):
        unix_passw= getpass.getpass("Unix Password: ")
        username= getpass.getuser()
        if not Shared.validUnixCredentials(username,unix_passw):
            Error("Invalid Unix Credentials")
        return username,unix_passw

    def getInputConfluenceToken(self):
        print(self.defaults['ConfTokenHelpPage'])
        confluence_token= getpass.getpass("Confluence Token: ")
        if not Confluence.Confluence.isCredentialsValid(self.defaults['ConfluenceServer'],confluence_token):
            Error("Invalid Confluence Credentials")
        return confluence_token
        
    def inputCredentials(self):
        username,unix_passw=self.getInputUnixCredentials()
        confluence_token=self.getInputConfluenceToken()
        return username,unix_passw,confluence_token

    def inputCredentialsdummy(self):
        username= getpass.getuser()
        unix_passw="dummy"
        confluence_token="dummy"
        return username,unix_passw,confluence_token

    def getEmail(self,username):
            email = os.popen('ldapsearch -xLL -h ' + self.defaults['LdapServer'] + ' -b dc=' + self.defaults['Ldapdc'][0] + ",dc="+  self.defaults['Ldapdc'][1] + ' uid=' + username  + ' mail').read().strip()
            email=email.splitlines()[-1]
            if "mail" in email:
                email=re.sub(".*mail: ","",email)
            else:
                Error("Could not get email Id from username " + username)
            return email




if __name__ == "__main__":

    ConsoleLogFile = open("./console.log", "w")
    argparser = argparse.ArgumentParser(description="Jira")
    argparser.add_argument('keywords', nargs='+')
    argparser.add_argument("-regex",
                           metavar="regex",
                           required=False,
                           help="DashboardDataDir",
                           nargs='+',
                           default=[])

    argparser.add_argument("-getregex",
                           metavar="regex",
                           required=False,
                           help="DashboardDataDir",
                           nargs='+',
                           default=[])

    argparser.add_argument(
        "-commentedBy",
        metavar="UserName",
        default="",
        required=False,
        help=
        "Find tickets which are commented by persons. Pass comma separated names in double quotes"
    )

    argparser.add_argument("-appendInJquery",
                           metavar="commentedby fasnfjksngkj",
                           default="",
                           required=False,
                           help="Append this as part of jquery")

    argparser.add_argument("-appendInCquery",
                           metavar="commentedby fasnfjksngkj",
                           default="",
                           required=False,
                           help="Append this as part of jquery")

    argparser.add_argument("-customJquery",
                           metavar="text ~ nitin AND commentedBy fasnfjksngkj",
                           default="",
                           required=False,
                           help="Use this is the only jquery")

    argparser.add_argument("-customCquery",
                           metavar="text ~ nitin AND commentedBy fasnfjksngkj",
                           default="",
                           required=False,
                           help="Use this is the only cquery")

    argparser.add_argument("-verbose",
                           action='store_true',
                           help="Enable detailed log")

    argparser.add_argument("-debug",
                           action='store_true',
                           help="Enable Debugging mode")

    args = argparser.parse_args()
    # print(args)
    commentedBy = list(filter(None, args.commentedBy.split(",")))
    ## used filter to remove empty contents from list
    Logging.debug = args.debug
    UniSearch(keywords=args.keywords,
              commentedBy=commentedBy,
              regexs=args.regex,
              appendInJquery=args.appendInJquery,
              appendInCquery=args.appendInCquery,
              customJquery=args.customJquery,
              customCquery=args.customCquery,
              getregexs=args.getregex)

    ConsoleLogFile.close()
# %%
