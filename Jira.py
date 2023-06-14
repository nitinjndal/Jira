#! /usr/bin/env python
#
import sys
import os
import re
import argparse
import json
import functools


import datetime as dt
import jira
from Shared import Logging,DebugMsg,DebugMsg2,Info,Shared,Error,bold,boldr
import threading
from concurrent.futures import ThreadPoolExecutor

## import shutil
#from sympy import primenu
## import pandas as pd
## import time
## import numpy as np
## import tarfile
## from difflib import SequenceMatcher
## import Common.local_functions as LF



class Jira:

	def __init__(self, keywords,regexs=[],commentedBy=[],appendInJquery="",customJquery=None,getregexs=[],credentialsFile=None,credentialsHead=None,max_results=50):
		self.max_results=max_results

		defaultsFile = Shared.defaultsFilePath

		if credentialsHead is None:
			credentialsHead="Jira"

		self.defaults=Shared.read_defaults(defaultsFile,credentialsHead)
		if credentialsFile is None:
			credentialsFile = self.defaults["CredentialsFile"]

		self.credentials=Shared.read_credentials(credentialsFile,credentialsHead)
		if not Shared.validUnixCredentials(self.credentials["username"],self.credentials["token"]):
			Error("Invalid Unix Credentials")

		if not Shared.isVpnConnected(self.credentials["server"]):
			return

		self.jira = jira.JIRA(basic_auth=(self.credentials["username"], self.credentials["token"]), options={'server': self.credentials["server"]})
		self.expand_comments = False
		self.keywords=keywords
		self.__get_regexs=getregexs
		DebugMsg("commentedBy=",commentedBy)
		jql_query=self.create_jql(customJquery,appendInJquery)
		DebugMsg("Search Jira")
		issues=self.get_issues_tp(jql_query)
		self.get_matching_issues_tp(issues,regexs)


	def create_jql(self,customJquery=None, appendInJquery=""):
		# keywords=["abc", "def"]
		projects = self.jira.projects()
		allowed_projects=[]
		for project in projects:
			allowed_projects.append(project.key)
		i=0
		jql_query=""
		if customJquery is not None and re.match(".*\S.*",customJquery):
			jql_query=customJquery
		else:
			jql_query+= "("
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
			jql_query+= ") AND ("
			i=0
			jql_query+= "project in (" 
			for project in self.defaults['projects']:
				if project in allowed_projects:
					if i > 0:
						jql_query+= ","
					i+=1
					jql_query+= project
			jql_query+= "))"

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

		found=False
		if len(self.__get_regexs + regexs + keywords )> 0:
			found=False
			comments=self.jira.comments(issue)

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

	def jira_search_issues(self,jql_query,max_results_per_iter,start_at):
		DebugMsg("Searching " + str(start_at))
		return self.jira.search_issues(jql_query ,  maxResults=max_results_per_iter,startAt=start_at)

	def get_issues_tp(self,jql_query):
		DebugMsg("Jql_query = " + jql_query)
		max_results_per_iter=20
		start_ats=[]
		for i in range(0,int(self.max_results/max_results_per_iter)):
			start_ats.append(max_results_per_iter*i)

		max_threads=10
		with ThreadPoolExecutor(max_workers=max_threads) as exe:
			fp=functools.partial(self.jira_search_issues,
									jql_query,
									max_results_per_iter)
			issues_iters=exe.map(fp,start_ats)

		issues=[]
		for issues_iter in issues_iters:
			issues=issues + issues_iter

		limit_msg=""
		if len(issues) == self.max_results:
			limit_msg=" (Max Limit reached)"
		DebugMsg("Number of issues : " + str(len(issues)) + limit_msg)
		return issues

	def get_issues(self,jql_query):
		DebugMsg("Jql_query = " + jql_query)
		max_results_per_iter=100
		start_at=0
		issues=[]

		while True:
			issues_iter=self.jira.search_issues(jql_query ,  maxResults=max_results_per_iter,startAt=start_at)
			issues=issues + issues_iter
			if (len(issues_iter)< max_results_per_iter):
				break
			else:
				start_at += max_results_per_iter
				DebugMsg("Iter=",start_at )

			if len(issues)> 200:
				break
				self.printIssues(issues)
				raise ValueError("Too many results found (" + str(len(issues)) + "). Please add more filters in jql query")

		DebugMsg("Number of issues : " + str(len(issues)))
		return issues

	def printIssues(self,issues,header=""):
		if len(issues)>0:
			issues=issues.copy()
			issues.reverse
			Info(boldr("\n################## " + header + " " + "###################################"),print_dt=False)
			i=0
			for issue in issues:
				i+=1
				Info(str(i) + ")" + bold(" " + issue.permalink() + " ") + "\t" + issue.fields.summary,print_dt=False)
				if self.expand_comments:
					for comment in self.jira.comments(issue):
						DebugMsg("####################################################################################",print_dt=False)
						DebugMsg("Commented by " + str(comment.author) + " on " + comment.created,print_dt=False)
						DebugMsg("####################################################################################",print_dt=False)
						DebugMsg(comment.body,print_dt=False)
					DebugMsg("#####################################################",print_dt=False)
			DebugMsg("################## Ends ###################################",print_dt=False)
			sys.stdout.flush()



	def __search_regexp(self,issue,regexs,matched_issues,not_matched_issues,other_info):
		#with self.__sema:
		#DebugMsg2("Thread Started = " + str(other_info['thread']))
		DebugMsg( threading.current_thread().ident)
		if self.search_regexp(issue,regexs):
			matched_issues.append(issue)
		else:
			not_matched_issues.append(issue)
		#DebugMsg2("Thread Ended= " + str(other_info['thread']))
		DebugMsg( threading.current_thread().ident)

	def __search_regexp_tp(self,regexs,matched_issues,not_matched_issues,other_info,issue):
		#with self.__sema:
		#DebugMsg2( "Thread Started = " + str(threading.current_thread().ident) + " : " + str( issue.key))
		if self.search_regexp(issue,regexs):
			matched_issues.append(issue)
		else:
			not_matched_issues.append(issue)
		#DebugMsg2( "Thread Ended = " + str(threading.current_thread().ident) + " : " + str( issue.key))

	def get_matching_issues_tp(self,issues,regexs):
		matched_issues=[]
		not_matched_issues=[]
		max_threads=10
		DebugMsg("Finding Regex")
		with ThreadPoolExecutor(max_workers=max_threads) as exe:
			fp=functools.partial(self.__search_regexp_tp,
									regexs,
									matched_issues,
									not_matched_issues,
									{'thread':'??'})
			exe.map(fp,issues)


		self.__printIssues(issues,matched_issues,not_matched_issues)

	def get_matching_issues_mt(self,issues,regexs):
		matched_issues=[]
		not_matched_issues=[]
		threads=[]
		max_threads=100
		self.__sema = threading.Semaphore(max_threads)
		i=0
		for issue in issues:
			#self.__search_regexp(issue,regexs,matched_issues,not_matched_issues)
			i+=1
			t1 = threading.Thread(target=self.__search_regexp,
								  kwargs=dict(
									  issue=issue,
									  regexs=regexs,
									  matched_issues=matched_issues,
									  not_matched_issues=not_matched_issues,
									  other_info={'thread':i}))
			threads.append(t1)
			t1.start()

		for thread in threads:
			thread.join()

		self.__printIssues(issues,matched_issues,not_matched_issues)

	def get_matching_issues(self,issues,regexs):
		matched_issues=[]
		not_matched_issues=[]
		for issue in issues:
			if self.search_regexp(issue,regexs):
				matched_issues.append(issue)
				if len(matched_issues) >  50:
					break
					self.printIssues(matched_issues)
					raise ValueError("Too many results found (" + str(len(issues)) + "). Only 1st 50 results shown. Please add more filters in jql query or add regex to reduce the results")
			else:
				not_matched_issues.append(issue)
		self.__printIssues(issues,matched_issues,not_matched_issues)

	def __printIssues(self,issues,matched_issues,not_matched_issues):
		header=""
		if len(matched_issues)>0 :
			if len(not_matched_issues)>0 and len(matched_issues)<  Shared.matched_to_omit:
				header="Jira results from the native search query"
		elif len(issues)>0:
			header="Jira results from the native search query"

		if len(matched_issues)< Shared.matched_to_omit:
			self.printIssues(not_matched_issues,header)

		if len(matched_issues)>0:
			header="Filtered Jira results exactly matching the search query"
			self.printIssues(matched_issues,header)



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

# %%

# %%
