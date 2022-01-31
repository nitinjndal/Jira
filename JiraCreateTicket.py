#! /arm/tools/anaconda/conda_py3.7/2019.03/linux64/bin/python -E
#
from email.policy import default
import sys
import os
import argparse
from requests.auth import HTTPBasicAuth

import jira
import requests
import json
from Shared import Logging,DebugMsg,Info,Shared

### to get all users info in json:
##https://armcloud.atlassian.net/rest/api/3/user/assignable/search?project=PEGASUS&maxResults=1000&startAt=5000


class JiraCreateTicket:

	def __init__(self,
				 logfile,
				 description=None,
				 summary=None,
				 credentialsFile=None,
				 credentialsHead=None):

		defaultsFile = Shared.defaultsFilePath

		if credentialsHead is None:
			credentialsHead="Jira"

		self.defaults=Shared.read_defaults(defaultsFile,credentialsHead)

		if credentialsFile is None:
			credentialsFile = self.defaults["CredentialsFile"]

		self.credentials=Shared.read_credentials(credentialsFile,credentialsHead)

		if not Shared.isVpnConnected(self.credentials["server"]):
			return

		self.jira = jira.JIRA(basic_auth=(self.credentials["username"], self.credentials["token"]), options={'server': self.credentials["server"]})
		self.create_ticket(logfile, summary, description)


	def get_accountname_IdMap(self):
		self.accountIdsMap={}
		start_at=0
		max_results_per_iter=1000
		auth = HTTPBasicAuth(self.credentials["username"],
												self.credentials["token"])
  
		if "atlassian" in self.credentials["server"]:
			accountIdkey='accountId'
		else:
			accountIdkey='name'
			
		while True:
				params = (
						('project', self.defaults['fields']['project']),
						('maxResults', max_results_per_iter),
						('startAt', start_at)
				)
				response = requests.get(self.credentials["server"] + '/rest/api/2/user/assignable/search', params=params,auth=auth)
				results_iter=json.loads(response.content)
				for account in results_iter:
						self.accountIdsMap[account['emailAddress'].lower() ] =  account[accountIdkey]
				print(len(self.accountIdsMap.keys()))
				if (len(results_iter) != max_results_per_iter):
						break
				else:
						start_at += max_results_per_iter
	
	def get_fields_jiralocal(self,summary,description):
		fields_values = self.defaults['fields']
		### Set defaults

		components=[]
		fields_values["customfield_10061"]="CAT B" ## Severity
		fields_values["customfield_10063"]="NOI" ## Site
		fields_values["customfield_10064"]="NAHPC" ## Cluster
		fields_values["priority"]="Low" 
		for component in components:
			fields_values["components"].append(component)

		## change from defaults if specified otherwise
#		fields_values["issuetype"]=issue_type
#		fields_values["project"]=project
#		fields_values["priority"]=priority

		fields_values["description"]= description
		fields_values["summary"]= summary
		return fields_values

	def get_fields_jiracloud(self,summary,description):
		fields_values = self.defaults['fields']
		### Set defaults
		issue_type=fields_values["issuetype"]
		project=	fields_values["project"]

		components=[]
		fields_values["customfield_10061"]="CAT B" ## Severity
		fields_values["customfield_10063"]="NOI" ## Site
		fields_values["customfield_10064"]="NAHPC" ## Cluster
		fields_values["priority"]="Low" 
		for component in components:
			fields_values["components"].append(component)

		## change from defaults if specified otherwise
		fields_values["issuetype"]=issue_type
		fields_values["project"]=project

		fields_values["description"]= description
		fields_values["summary"]= summary
		return fields_values

	def create_ticket(self, logfile, summary, description):
		#   project_name="PEGASUS"
		#	summary_value="How to update install/../corner rdb without changing mdbs"
		#	description_value="Hi Syam, How we can change corners.rdb file only after updating the EOS_CORNERS_RDB file wihtout impacting the mdbs. Can we do that if do not have char ran in the sandbox"
		if "atlassian" in self.credentials["server"]:
			fields_value = self.get_fields_jiracloud(summary=summary,description=description)
		else:
			fields_value = self.get_fields_jiralocal(summary=summary,description=description)

		issue = None
		#   issue = self.jira.create_issue(fields=fields_value)
#		Info("Ticket Created : " + issue.permalink())

		### This watcher list names needs to go to defaults, Ids it should get on the fly
		self.get_accountname_IdMap()
		watcher_list=self.defaults["watchers_list"]
		for watcher in watcher_list:
			print(watcher.lower())
			if watcher.lower() in self.accountIdsMap:
				print(self.accountIdsMap[watcher.lower()])

				#self.jira.add_watcher(issue.id, self.accountIdsMap[watcher])
				#print("added " + watcher)
	



if __name__ == "__main__":

	argparser = argparse.ArgumentParser(description="Confluence Search")
	argparser.add_argument('-logfile', help="Path of log file")
	argparser.add_argument(
		"-summary",
		metavar="regex",
		required=False,
		help="Issue summary, will be used as title of ticket",
		default=None)

	argparser.add_argument("-description",
							 metavar="regex",
							 required=False,
							 help="Issue description",
							 default=None)

	argparser.add_argument("-verbose",
							 action='store_true',
							 help="Enable detailed log")

	argparser.add_argument("-debug",
							 action='store_true',
							 help="Enable Debugging mode")

	args = argparser.parse_args()
	# print(args)
	Logging.debug = args.debug
	## used filter to remove empty contents from list

	JiraCreateTicket(args.logfile,
					 description=args.description,
					 summary=args.summary,
					 credentialsFile=None,
					 credentialsHead=None)
