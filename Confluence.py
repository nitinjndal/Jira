#! /usr/bin/env python
#
import os
import re
import argparse
import json


import datetime as dt
import atlassian 
from Shared import Logging,DebugMsg,Info
import Shared



class Confluence:

    def __init__(self, keywords,regexs=[],commentedBy=[],appendInCquery="",customCquery=None,getregexs=[],credentialsFile=None,credentialsHead=None):

        if credentialsFile is None:
            credentialsFile= "~/.Confluence.json"

        self.credentialsHead="ConfluenceCredentials"
        if credentialsHead is not None:
            self.credentialsHead=credentialsHead

        credentialsFile=os.path.abspath(os.path.expanduser(os.path.expandvars(credentialsFile)))
        self.read_credentials(credentialsFile)
        oauth2_dict = {
            "client_id": None,
            "token": {
                "access_token": self.token
            }
        }
        if not Shared.isVpnConnected(self.server):
            return
        self.confluence = atlassian.Confluence(url=self.server,oauth2=oauth2_dict)

        self.keywords=keywords
        self.__get_regexs=getregexs
        cql_query=self.create_cql(customCquery,appendInCquery)
        results=self.get_results(cql_query)
      #  self.get_matching_results(results,regexs)

    def read_credentials(self,filename):
        with open (filename) as f:
            creds=json.load(f)
        self.token=creds[self.credentialsHead]['token']
        self.server=creds[self.credentialsHead]['server']
        self.username=creds[self.credentialsHead]['username']

    def create_cql(self,customCquery=None, appendInCquery=""):
        # keywords=["abc", "def"]
        i=0
        cql_query=""
        if customCquery is not None and re.match(".*\S.*",customCquery):
            cql_query=customCquery
        else:
            for keyword in self.keywords:
                if i> 0:
                    cql_query+= " AND "
                cql_query+= "(title ~ \"" + keyword + "\" OR text ~ \"" + keyword + "\")"
                i+=1
            if re.match(".*\S",appendInCquery) and (not (re.match("^\s*AND",appendInCquery) or re.match("^\s*OR",appendInCquery))):
                appendInCquery=" AND " + appendInCquery

            cql_query+= " OR ("
            cql_query+= "(title ~ \"" + " ".join(self.keywords) + "\" OR text ~ \"" + " ".join(self.keywords) + "\")"
            cql_query+= ")"
            cql_query += appendInCquery
        #    cql_query +=" ORDER BY updatedDate DESC"
        return cql_query
### My assigned
#       cql_query = "assignee = 5d10dfab29d82d0c4e913d88 AND status not in (Done,Rejected,\"On Hold\" ) order by updated DESC"

    def search_regexp(self,result,regexs):
        ## keywords is added if some keywords has more than one word
        keywords=[]
        for keyword in self.keywords:
            keyword=keyword.strip()
            if re.search("\s",keyword) or re.search("\W",keyword):
                keywords.append(keyword)

        comments=self.confluence.comments(result)

        for pattern in self.__get_regexs:
            #            DebugMsg("Pattern", pattern)
            found=False
            for comment in comments:
                s1=re.search(pattern,comment.body,re.IGNORECASE)
                if s1:
                    DebugMsg(result.permalink(),s1.group(0))

            s2=None
            s3=None
            if (result.fields.description is not None):
                s2= re.search(pattern,result.fields.description,re.IGNORECASE)
            if (result.fields.summary is not None):
                s3= re.search(pattern,result.fields.summary,re.IGNORECASE)
            if s2:
                DebugMsg(result.permalink(),s2.group(0))
            if s3:
                DebugMsg(result.permalink(),s3.group(0))

        found=False
        for pattern in (regexs + keywords):
            found=False
            for comment in comments:
                if re.search(pattern,comment.body,re.IGNORECASE):
                    found=True


            if ( found
                or ((result.fields.description is not None) and re.search(pattern,result.fields.description,re.IGNORECASE))
                or ((result.fields.summary is not None) and re.search(pattern,result.fields.summary,re.IGNORECASE))
                ) :
                found=True

            if not found:
                return False

        return found
    
    def filter_relevant_results(self,all_results):
        relevantResults=[]
        for result in all_results:
            if self.is_result_relevant(result):
                relevantResults.append(self.server + result['url'])  
        return relevantResults


    def is_result_relevant(self,result):
        if 'weekly' not in result['url'].lower():
            return True
        else:
            return False


    def get_results(self,cql_query):
        DebugMsg("Cql_query = " + cql_query)
        max_results_per_iter=100
        start_at=0
        results=[]
        while True:
            results_iter=self.confluence.cql(cql_query, start=start_at, limit=max_results_per_iter, expand=None, include_archived_spaces=None, excerpt=None)
            results=results + results_iter["results"]
            if (len(results_iter)< max_results_per_iter):
                break
            else:
                start_at += max_results_per_iter
                DebugMsg("Iter=",start_at )

            if len(results)> 500:
                self.printResults(results)
                raise ValueError("Too many results found (" + str(len(results)) + "). Please add more filters in jql query")

        DebugMsg("Number of results : " + str(len(results)))
        results=self.filter_relevant_results(results)
        self.printResults(results)
        return results

    def printResults(self,results):
        if len(results)>0:
            DebugMsg("\n\n################## Confluence Results ###################################",print_dt=False)
            for result in results:
                Info(result,print_dt=False)
            DebugMsg("################## Confluence Results Ends ###################################\n\n",print_dt=False)



    def get_matching_results(self,results,regexs):
        matched_results=[]
        not_matched_results=[]
        for result in results:
            if self.search_regexp(result,regexs):
                matched_results.append(result)
                if len(matched_results) >  50:
                    self.printResults(matched_results)
                    raise ValueError("Too many results found (" + str(len(results)) + "). Only 1st 50 results shown. Please add more filters in jql query or add regex to reduce the results")
            else:
                not_matched_results.append(result)

        if len(matched_results)>0 :
            if len(not_matched_results)>0 and len(matched_results)< 5:
                DebugMsg("####################################################################################")
                DebugMsg("###### Confluence results not exactly matching the search query ###########")
                DebugMsg("####################################################################################")
        else:
            DebugMsg("")
            DebugMsg("###### No Confluence results matched the exact regex. ###########")
        if len(matched_results)< 5:
            self.printResults(not_matched_results)
        elif len(matched_results) >  50:
            self.printResults(matched_results)
            raise ValueError("Too many results found (" + str(len(results)) + "). Only 1st 50 results shown. Please add more filters in jql query or add regex to reduce the results")

        if len(matched_results)>0:
            DebugMsg("####################################################################################")
            DebugMsg("###### Confluence results matching the search query ###### ")
            DebugMsg("####################################################################################")
            self.printResults(matched_results)



if __name__ == "__main__":

    argparser = argparse.ArgumentParser(description="Confluence Search")
    argparser.add_argument('keywords', nargs='+')
    argparser.add_argument(
        "-regex", metavar="regex", required=False, help="DashboardDataDir",nargs='+', default=[])

    argparser.add_argument(
        "-getregex", metavar="regex", required=False, help="DashboardDataDir",nargs='+', default=[])

    argparser.add_argument(
        "-commentedBy", metavar="UserName",  default="", required=False,
        help="Find tickets which are commented by persons. Pass comma separated names in double quotes")

    argparser.add_argument(
        "-appendInCquery", metavar="commentedby fasnfjksngkj",  default="", required=False,
        help="Append this as part of jquery")

    argparser.add_argument(
        "-customCquery", metavar="text ~ nitin AND commentedBy fasnfjksngkj",  default="", required=False,
        help="Use this is the only jquery")

    argparser.add_argument(
        "-verbose", action='store_true', help="Enable detailed log")


    argparser.add_argument(
        "-debug", action='store_true', help="Enable Debugging mode")


    args = argparser.parse_args()
    # print(args)
    Logging.debug=args.debug
    commentedBy=list(filter(None,args.commentedBy.split(",")))
    ## used filter to remove empty contents from list


    Confluence(args.keywords,
     commentedBy=commentedBy,
     regexs=args.regex,
     appendInCquery=args.appendInCquery,
     customCquery=args.customCquery,
     getregexs=args.getregex
    )
