#! /usr/bin/env python
#
import sys
import os
import re
import argparse
import json


import datetime as dt
from jira import JIRA

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

        ConsoleLogFile.flush()

def DebugMsg2(msg1,msg2=None,printmsg=True):
    DebugMsg(msg1,msg2,printmsg)

def DebugMsg3(msg1,msg2=None,printmsg=True):
    DebugMsg(msg1,msg2,printmsg)

def Info(msg1,msg2=None,printmsg=True):
    DebugMsg(msg1,msg2,printmsg,ForcePrint=True)
class myJira:


    def __init__(self, keywords,regexs=[],commentedBy=[],appendInJquery="",customJquery=None,getregexs=[]):

        self.read_credentials("./PrivateInfo.json")

        self.jira_cloud = JIRA(basic_auth=(self.username, self.token), options={'server': self.jira_server})
        self.expand_comments = False
        self.keywords=keywords
        self.__get_regexs=getregexs
        Info("commentedBy=",commentedBy)
        jql_query=self.create_jql(customJquery,appendInJquery)
        issues=self.get_issues(jql_query)
        self.get_matching_issues(issues,regexs)
    
    def read_credentials(self,filename):
        with open (filename) as f:
            creds=json.load(f)
        self.token=creds['credentials']['token']
        self.jira_server=creds['credentials']['jira_server']
        self.username=creds['credentials']['username']

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
        
        comments=self.jira_cloud.comments(issue)

        for pattern in self.__get_regexs:
#            Info("Pattern", pattern)
            found=False
            for comment in comments:
                s1=re.search(pattern,comment.body,re.IGNORECASE)
                if s1:
                    Info(issue.permalink(),s1.group(0))
            
            s2=None
            s3=None
            if (issue.fields.description is not None):
                s2= re.search(pattern,issue.fields.description,re.IGNORECASE)
            if (issue.fields.summary is not None):
                s3= re.search(pattern,issue.fields.summary,re.IGNORECASE)
            if s2:
                Info(issue.permalink(),s2.group(0))
            if s3:
                Info(issue.permalink(),s3.group(0))

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

        Info("Jql_query = " + jql_query)
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

        Info("Number of issues : " + str(len(issues)))

        
        return issues
    
    def printIssues(self,issues):
        issues=issues.copy()
        issues.reverse
        for issue in issues:
            Info(issue.permalink() + "\t" + issue.fields.summary)
            if self.expand_comments:
                for comment in self.jira_cloud.comments(issue):
                    Info("####################################################################################")
                    Info("Commented by " + str(comment.author) + " on " + comment.created)
                    Info("####################################################################################")
                    Info(comment.body)
                Info("\n#####################################################\n")


    def get_matching_issues(self,issues,regexs):
        matched_issues=[]
        not_matched_issues=[]
        for issue in issues:
            if self.search_regexp(issue,regexs):
                matched_issues.append(issue)
            else:
                not_matched_issues.append(issue)

        if len(matched_issues)>0 :
            if len(not_matched_issues)>0 and len(matched_issues)< 5:
                Info("####################################################################################")
                Info("###### Issues not exactly matching the search query ###########")
                Info("####################################################################################")
        else:
            Info("")
            Info("###### No issues matched the exact regex. ###########")
        if len(matched_issues)< 5:
            self.printIssues(not_matched_issues)
        elif len(matched_issues) >  50:
            self.printIssues(matched_issues)
            raise ValueError("Too many results found (" + str(len(issues)) + "). Please add more filters in jql query or add regex")

        if len(matched_issues)>0:
            Info("####################################################################################")
            Info("###### Issues matching the search query ###### ")
            Info("####################################################################################")
            self.printIssues(matched_issues)



if __name__ == "__main__":

    argparser = argparse.ArgumentParser(description="Jira")
    argparser.add_argument('keywords', nargs='+')
    argparser.add_argument(
        "-regex", metavar="regex", required=False, help="DashboardDataDir",nargs='+', default=[])

    argparser.add_argument(
        "-getregex", metavar="regex", required=False, help="DashboardDataDir",nargs='+', default=[])

    argparser.add_argument(
        "-commentedBy", metavar="Nitin",  default="", required=False,
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
#    debug=args.debug
    commentedBy=list(filter(None,args.commentedBy.split(",")))
    ## used filter to remove empty contents from list
    myJira(args.keywords,
     commentedBy=commentedBy,
     regexs=args.regex,
     appendInJquery=args.appendInJquery,
     customJquery=args.customJquery,
     getregexs=args.getregex
     )


    ConsoleLogFile.close()