#! /usr/bin/env python
#
import os
import re
import argparse
import json


import datetime as dt
import atlassian 
from Shared import Logging,DebugMsg,DebugMsg2,Info,Shared
from concurrent.futures import ThreadPoolExecutor
import functools



class Confluence:

	def __init__(self, keywords,regexs=[],commentedBy=[],appendInCquery="",customCquery=None,getregexs=[],credentialsFile=None,credentialsHead=None):

		defaultsFile = Shared.defaultsFilePath
		if credentialsHead is None:
			credentialsHead="Confluence"

		self.defaults=Shared.read_defaults(defaultsFile,credentialsHead)
		if credentialsFile is None:
			credentialsFile = self.defaults["CredentialsFile"]

		self.credentials=Shared.read_credentials(credentialsFile,credentialsHead)

		if not Shared.isVpnConnected(self.credentials["server"]):
			return


		oauth2_dict = {
			"client_id": None,
			"token": {
				"access_token": self.credentials["token"]
			}
		}
		self.confluence = atlassian.Confluence(url=self.credentials["server"],oauth2=oauth2_dict)

		self.keywords=keywords
		self.__get_regexs=getregexs
		cql_query=self.create_cql(customCquery,appendInCquery)
		results=self.get_results_tp(cql_query)
#		self.printResults(results)
		self.get_matching_results_tp(results,regexs)


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

		if result['content']['type']=='page':
			id=result['content']['id']
			page=self.confluence.get_page_by_id(page_id=id,expand='body.view')
			html_output=page['body']['view']['value']
			content=Shared.html_to_plain_text(html_output)
#			DebugMsg("content=",content)
			for pattern in self.__get_regexs:
				#            DebugMsg("Pattern", pattern)
				found=False
				s1=re.search(pattern,content,re.IGNORECASE)
				if s1:
					DebugMsg(result.permalink(),s1.group(0))

			found=False
			for pattern in (regexs + keywords):
				found=False
				if re.search(pattern,content,re.IGNORECASE):
					DebugMsg2("Found ", pattern )
					found=True
				else:
					DebugMsg2("Not Found ", pattern )



				if not found:
					return False
		else:
			return False

		return found
	
	def filter_relevant_results(self,all_results):
		relevantResults=[]
		for result in all_results:
			if self.is_result_relevant(result):
				relevantResults.append(result)  
		return relevantResults


	def is_result_relevant(self,result):
		if 'weekly' not in result['url'].lower():
			return True
		else:
			return False

	def search_cql_confluence(self,cql_query,max_results_per_iter,start_at):
		DebugMsg("Searching " + str(start_at))
		return self.confluence.cql(cql_query, limit=max_results_per_iter, expand=None, include_archived_spaces=None, excerpt=None,start=start_at)

	def get_results_tp(self,cql_query):
		DebugMsg("Cql_query = " + cql_query)
		max_results=400
		max_results_per_iter=40
		start_ats=[]
		for i in range(0,int(max_results/max_results_per_iter)):
			start_ats.append(max_results_per_iter*i)

		max_threads=10
		with ThreadPoolExecutor(max_workers=max_threads) as exe:
			fp=functools.partial(self.search_cql_confluence,
									cql_query,
									max_results_per_iter)
			results_iters=exe.map(fp,start_ats)

		results=[]
		for results_iter in results_iters:
			results=results + results_iter["results"]


		results=self.filter_relevant_results(results)
		DebugMsg("Number of results : " + str(len(results)))
		return results

	def printResults(self,results):
		if len(results)>0:
			DebugMsg("\n\n################## Confluence Results ###################################",print_dt=False)
			i=0
			for result in results:
				i+=1
				printval=self.credentials["server"] + result['url']
				Info(str(i) + ") " + printval,print_dt=False)
			DebugMsg("################## Confluence Results Ends ###################################\n\n",print_dt=False)


	def __search_regexp_tp(self,regexs,matched_results,not_matched_results,other_info,result):
		#with self.__sema:
		if self.search_regexp(result,regexs):
			matched_results.append(result)
		else:
			not_matched_results.append(result)

	def get_matching_results_tp(self,results,regexs):
		matched_results=[]
		not_matched_results=[]
		max_threads=10
		with ThreadPoolExecutor(max_workers=max_threads) as exe:
			fp=functools.partial(self.__search_regexp_tp,
									regexs,
									matched_results,
									not_matched_results,
									{'thread':'??'})
#			exe.map(fp,[results[0]])
			exe.map(fp,results)


		self.__printResults(results,matched_results,not_matched_results)

	def __printResults(self,results,matched_results,not_matched_results):

		if len(matched_results)>0 :
			if len(not_matched_results)>0 and len(matched_results)< 5:
				DebugMsg("####################################################################################")
				DebugMsg("###### Confluence results not exactly matching the search query ###########")
				DebugMsg("####################################################################################")
		elif len(results)>0:
			DebugMsg("")
			DebugMsg("###### No Confluence results matched the exact regex. ###########")

		if len(matched_results)< 5:
			self.printResults(not_matched_results)
		#elif len(matched_results) >  50:
			#self.printResults(matched_results)
			#raise ValueError("Too many results found (" + str(len(results)) + "). Only 1st 50 results shown. Please add more filters in jql query or add regex to reduce the results")

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
