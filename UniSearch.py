#! /arm/pipd/tools/software/UniSearch/2.0.0/bin/python
#! /usr/bin/env python
#
#! TODO : print matching lines
#! Omit non relevant results , native search query even 1 results is found
 
##  To do 
##  Add option to print the mathced lines
##  Add option to print only the exactly matched results

import datetime as dt
begin_time = dt.datetime.now()
print(begin_time.strftime("%c") + " \nSearching ...", flush=True)
from Shared import Logging, DebugMsg, Info, Error,Shared,bold
import logging
import time
import sys
import os
import re
import argparse
import json
import getpass 
# %%
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

def eap_call():
    eap_path=os.path.dirname(__file__) + "/eap.sh"
    t=os.popen(eap_path + " " +  " ".join(sys.argv))
eap_call()

class UniSearch:

    def __init__(self,
                 keywords,
                 regexs=[],
                 commentedBy=[],
                 appendInJquery="",
                 appendInCquery="",
                 customJquery=None,
                 customCquery=None,
                 getregexs=[],
                 search_options={}):
        
        self.search_options=search_options
        Shared.matched_to_omit=self.search_options.get('omit_native_after')

        defaultsFile = Shared.defaultsFilePath
        credentialsHead = "UniSearch"
        self.defaults = Shared.read_defaults(defaultsFile, credentialsHead)
        self.credentialsFile = Shared.abs_path(self.defaults["CredentialsFile"])
        exit_after_auth=False
        if not os.path.exists(self.credentialsFile):
#            exit_after_auth=True
            DebugMsg(".UniSearch.json does not exist")
            username,unix_pw,confluence_token=self.inputCredentialsdummy()
            email=self.getEmail(username)
            Shared.CreateCredentialsFile(username,email,unix_pw,
                                         confluence_token,self.defaults,self.credentialsFile)

        creds= Shared.read_credentials_File(self.credentialsFile)

        acquire_token_flow=SharepointSearch.SharepointSearch(credentialsFile=self.credentialsFile, keywords=[],SearchSharepoint=False,SearchFindit=False,SearchMail=False)
        acquire_token_flow.acquire_token(scope=["Sites.Read.All","Mail.Read"])
        time.sleep(1)
        acquire_token_flow.acquire_token(scope=["https://armh.sharepoint.com/Sites.Read.All"])

        creds= Shared.read_credentials_File(self.credentialsFile)
        if not Shared.validUnixCredentials(getpass.getuser(),creds['Jira']['credentials']['token']):
            username,unix_passw=self.getInputUnixCredentials()
            creds=Shared.updateCredentialsJson(unix_passw=unix_passw,jsondata=creds)
            Shared.update_credentials(self.credentialsFile,creds)
        
        if exit_after_auth:
            exit(0)

    #    if not Confluence.Confluence.isUserCredentialsValid(self.defaults['ConfluenceServer'],getpass.getuser(),creds['Jira']['credentials']['token']):
    #        confluence_token=self.getInputConfluenceToken()
    #        creds=Shared.updateCredentialsJson(conf_token=confluence_token,jsondata=creds)
    #        Shared.update_credentials(self.credentialsFile,creds)



        #	JiraCloudThread = threading.Thread(target=Jira.Jira,
        #					  kwargs=dict(keywords=keywords,
        #								  commentedBy=commentedBy,
        #								  regexs=regexs,
        #								  appendInJquery=appendInJquery,
        #								  customJquery=customJquery,
        #								  getregexs=getregexs,
        #								  credentialsFile=self.credentialsFile,
        #								  credentialsHead="JiraCloud"))

        SharePointThread=None
        FinditThread=None
        MailThread=None
        JiraThread=None
        ConfluenceThread=None
        max_results=50
        if 'max_results' in self.search_options:
            max_results=self.search_options['max_results']
            if max_results < 1 or max_results > 5000:
                max_results=5000
        
        if ('search_sharepoint' not in self.search_options 
              or self.search_options['search_sharepoint']): 
            SharePointThread = threading.Thread(
                target=SharepointSearch.SharepointSearch,
                kwargs=dict(keywords=keywords,
                            credentialsFile=self.credentialsFile,
                            regexs=regexs,
                            getregexs=getregexs,
                            SearchSharepoint=True,
                            SearchFindit=False,
                            SearchMail=False,max_results=max_results))

        if ('search_wiki' not in self.search_options 
              or self.search_options['search_sharepoint']): 
            FinditThread = threading.Thread(
                target=SharepointSearch.SharepointSearch,
                kwargs=dict(keywords=keywords,
                            credentialsFile=self.credentialsFile,
                            regexs=regexs,
                            getregexs=getregexs,
                            SearchSharepoint=False,
                            SearchFindit=True,
                            SearchMail=False,max_results=max_results))

        if ('search_email' not in self.search_options 
              or self.search_options['search_email']): 
            MailThread = threading.Thread(target=SharepointSearch.SharepointSearch,
                                        kwargs=dict(
                                            keywords=keywords,
                                            credentialsFile=self.credentialsFile,
                                            regexs=regexs,
                                            getregexs=getregexs,
                                            SearchSharepoint=False,
                                            SearchFindit=False,
                                            SearchMail=True,max_results=max_results))

        if ('search_jira' not in self.search_options 
              or self.search_options['search_jira']): 
            JiraThread = threading.Thread(target=Jira.Jira,
                                        kwargs=dict(
                                            keywords=keywords,
                                            commentedBy=commentedBy,
                                            regexs=regexs,
                                            getregexs=getregexs,
                                            appendInJquery=appendInJquery,
                                            customJquery=customJquery,
                                            credentialsFile=self.credentialsFile,
                                            credentialsHead="Jira",max_results=max_results))

        if ('search_confluence' not in self.search_options 
              or self.search_options['search_confluence']): 
            ConfluenceThread = threading.Thread(
                target=Confluence.Confluence,
                kwargs=dict(keywords=args.keywords,
                            regexs=regexs,
                            appendInCquery=appendInCquery,
                            customCquery=customCquery,
                            getregexs=getregexs,
                            credentialsFile=self.credentialsFile,max_results=max_results))

        #	JiraCloudThread.start()
        if JiraThread is not None:
            JiraThread.start()


        if SharePointThread is not None:
            SharePointThread.start()

        if FinditThread is not None:
            FinditThread.start()

        if ConfluenceThread is not None:
            ConfluenceThread.start()

        if MailThread is not None:
            MailThread.start()


        #	JiraCloudThread.join()
        if JiraThread is not None:
            JiraThread.join()

        if SharePointThread is not None:
            SharePointThread.join()

        if FinditThread is not None:
            FinditThread.join()

        if ConfluenceThread is not None:
            ConfluenceThread.join()

        if MailThread is not None:
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


    argparser.add_argument("-no_email",
                            dest="email",
                           action='store_false',
                           help="Dont search in email")


    argparser.add_argument("-no_sharepoint",
                            dest="sharepoint",
                           action='store_false',
                           help="Dont search in sharepoint")

    argparser.add_argument("-no_jira",
                            dest="jira",
                           action='store_false',
                           help="Dont search in jira")

    argparser.add_argument("-no_wiki",
                            dest="wiki",
                           action='store_false',
                           help="Dont search in wiki")

    argparser.add_argument("-no_confluence",
                            dest="confluence",
                           action='store_false',
                           help="Dont search in confluence")

    argparser.add_argument("-max_results",
                           default=50, type=int,
                          help="Limit of results per forum (cannot be more than 5000). default 50,")

    argparser.add_argument("-omit_native_after",
                           default=5, type=int,
                          help="Omit the native results after the given exact matches")
    


    args = argparser.parse_args()
    # print(args)
    search_options=dict()
    search_options['search_jira']=args.jira
    search_options['search_email']=args.email
    search_options['search_sharepoint']=args.sharepoint
    search_options['search_wiki']=args.wiki
    search_options['search_confluence']=args.confluence
    search_options['max_results']=args.max_results
    search_options['omit_native_after']=args.omit_native_after
    DebugMsg(search_options)
    
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
              getregexs=args.getregex,
              search_options=search_options)

# %%
