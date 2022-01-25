#! /usr/bin/env python
#
import sys
import os
import re
import argparse
import json


import datetime as dt
import jira
from Shared import Logging,DebugMsg,Info
import requests
import Shared

## import shutil
#from sympy import primenu
## import pandas as pd
## import time
## import numpy as np
## import tarfile
## from difflib import SequenceMatcher
## import Common.local_functions as LF



class Jira:

    def __init__(self, keywords,regexs=[],commentedBy=[],appendInJquery="",customJquery=None,getregexs=[],credentialsFile=None,credentialsHead=None):

        if credentialsFile is None:
            credentialsFile= "~/.Jira.json"

        self.credentialsHead="JiraCloudCredentials"
        self.credentialsHead="JiraCredentials"
        if credentialsHead is not None:
            self.credentialsHead=credentialsHead

        credentialsFile=os.path.abspath(os.path.expanduser(os.path.expandvars(credentialsFile)))
        self.read_credentials(credentialsFile)
        rep=requests.get(self.server)
        if not Shared.isVpnConnected(self.server):
            return

        self.jira_cloud = jira.JIRA(basic_auth=(self.username, self.token), options={'server': self.server})
        self.expand_comments = False
        self.keywords=keywords
        self.__get_regexs=getregexs
        DebugMsg("commentedBy=",commentedBy)
        jql_query=self.create_jql(customJquery,appendInJquery)
        issues=self.get_issues(jql_query)
        self.get_matching_issues(issues,regexs)
    
    def read_credentials(self,filename):
        with open (filename) as f:
            creds=json.load(f)
        self.token=creds[self.credentialsHead]['token']
        self.server=creds[self.credentialsHead]['server']
        self.username=creds[self.credentialsHead]['username']

    def create_jql(self,customJquery=None, appendInJquery=""):
       # keywords=["abc", "def"]
        i=0
        jql_query=""
        if customJquery is not None and re.match(".*\S.*",customJquery):
            jql_query=customJquery
        else:
            for keyword in self.keywords:
                if i> 0:
                    jql_query+= " AND "
                jql_query+= "(comment ~ \"" + keyword + "\" OR text ~ \"" + keyword + "\")"
                i+=1
            if re.match(".*\S",appendInJquery) and (not (re.match("^\s*AND",appendInJquery) or re.match("^\s*OR",appendInJquery))):
                appendInJquery=" AND " + appendInJquery
            
            jql_query+= " OR ("
            jql_query+= "(comment ~ \"" + " ".join(self.keywords) + "\" OR text ~ \"" + " ".join(self.keywords) + "\")"
            jql_query+= ")"
            jql_query += appendInJquery
            jql_query +=" ORDER BY updatedDate DESC"
        return jql_query
### My assigned 
#       jql_query = "assignee = 5d10dfab29d82d0c4e913d88 AND status not in (Done,Rejected,\"On Hold\" ) order by updated DESC"

    def search_regexp(self,issue,regexs):
        ## keywords is added if some keywords has more than one word
        keywords=[]
        for keyword in self.keywords:
            keyword=keyword.strip()
            if re.search("\s",keyword) or re.search("\W",keyword):
                keywords.append(keyword)
        
        found=True
        if len(self.__get_regexs + regexs + keywords )> 0: 
            found=False
            comments=self.jira_cloud.comments(issue)

            for pattern in self.__get_regexs:
    #            DebugMsg("Pattern", pattern)
                found=False
                for comment in comments:
                    s1=re.search(pattern,comment.body,re.IGNORECASE)
                    if s1:
                        DebugMsg(issue.permalink(),s1.group(0))
                
                s2=None
                s3=None
                if (issue.fields.description is not None):
                    s2= re.search(pattern,issue.fields.description,re.IGNORECASE)
                if (issue.fields.summary is not None):
                    s3= re.search(pattern,issue.fields.summary,re.IGNORECASE)
                if s2:
                    DebugMsg(issue.permalink(),s2.group(0))
                if s3:
                    DebugMsg(issue.permalink(),s3.group(0))

            for pattern in (regexs + keywords):
                found=False
                for comment in comments:
                    if re.search(pattern,comment.body,re.IGNORECASE):
                        found=True

                
                if ( found 
                    or ((issue.fields.description is not None) and re.search(pattern,issue.fields.description,re.IGNORECASE))
                    or ((issue.fields.summary is not None) and re.search(pattern,issue.fields.summary,re.IGNORECASE))
                    ) :
                    found=True

                if not found:
                    return False

        return found

    def get_issues(self,jql_query):
        DebugMsg("Jql_query = " + jql_query)
        max_results_per_iter=100
        start_at=0
        issues=[]
        while True:
            issues_iter=self.jira_cloud.search_issues(jql_query ,  maxResults=max_results_per_iter,startAt=start_at)
            issues=issues + issues_iter
            if (len(issues_iter)< max_results_per_iter):
                break
            else:
                start_at += max_results_per_iter
                DebugMsg("Iter=",start_at )

            if len(issues)> 500:
                break
                self.printIssues(issues)
                raise ValueError("Too many results found (" + str(len(issues)) + "). Please add more filters in jql query")

        DebugMsg("Number of issues : " + str(len(issues)))
        return issues
    
    def printIssues(self,issues):
        if len(issues)>0:
            issues=issues.copy()
            issues.reverse
            DebugMsg("\n\n################## Jira Issues ###################################",print_dt=False)
            for issue in issues:
                Info(issue.permalink() + "\t" + issue.fields.summary,print_dt=False)
                if self.expand_comments:
                    for comment in self.jira_cloud.comments(issue):
                        DebugMsg("####################################################################################",print_dt=False)
                        DebugMsg("Commented by " + str(comment.author) + " on " + comment.created,print_dt=False)
                        DebugMsg("####################################################################################",print_dt=False)
                        DebugMsg(comment.body,print_dt=False)
                    DebugMsg("\n#####################################################\n",print_dt=False)
            DebugMsg("################## Jira Issues Ends ###################################\n\n",print_dt=False)
            sys.stdout.flush()
            


    def get_matching_issues(self,issues,regexs):
        matched_issues=[]
        not_matched_issues=[]
        for issue in issues:
            if self.search_regexp(issue,regexs):
                matched_issues.append(issue)
                if len(matched_issues) >  50:
                    self.printIssues(matched_issues)
                    raise ValueError("Too many results found (" + str(len(issues)) + "). Only 1st 50 results shown. Please add more filters in jql query or add regex to reduce the results")
            else:
                not_matched_issues.append(issue)

        if len(matched_issues)>0 :
            if len(not_matched_issues)>0 and len(matched_issues)< 5:
                DebugMsg("####################################################################################")
                DebugMsg("###### Jira issues not exactly matching the search query ###########")
                DebugMsg("####################################################################################")
        elif len(issues)>0:
            DebugMsg("")
            DebugMsg("###### No Jira issues matched the exact regex. ###########")

        if len(matched_issues)< 5:
            self.printIssues(not_matched_issues)
        elif len(matched_issues) >  50:
            self.printIssues(matched_issues)
            raise ValueError("Too many results found (" + str(len(issues)) + "). Only 1st 50 results shown. Please add more filters in jql query or add regex to reduce the results")

        if len(matched_issues)>0:
            DebugMsg("####################################################################################")
            DebugMsg("###### Jira issues matching the search query ###### ")
            DebugMsg("####################################################################################")
            self.printIssues(matched_issues)



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
        "-customJquery", metavar="text ~ nitin AND commentedBy fasnfjksngkj",  default="", required=False,
        help="Use this is the only jquery")

    argparser.add_argument(
        "-verbose", action='store_true', help="Enable detailed log")


    argparser.add_argument(
        "-debug", action='store_true', help="Enable Debugging mode")


    args = argparser.parse_args()
    # print(args)
    debug=args.debug
    commentedBy=list(filter(None,args.commentedBy.split(",")))
    ## used filter to remove empty contents from list
    Logging.debug=args.debug


    Jira(args.keywords,
     commentedBy=commentedBy,
     regexs=args.regex,
     appendInJquery=args.appendInJquery,
     customJquery=args.customJquery,
     getregexs=args.getregex
    )


    
