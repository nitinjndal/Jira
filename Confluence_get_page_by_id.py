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

	def __init__(self, pageid,credentialsFile=None,credentialsHead=None):

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
		page=self.confluence.get_page_by_id(page_id=pageid,expand='body.view')
		html_output=page['body']['view']['value']
		DebugMsg("html=",html_output)
		content=Shared.html_to_plain_text(html_output)
		Info(content)




if __name__ == "__main__":

	argparser = argparse.ArgumentParser(description="Confluence Search")
	argparser.add_argument('pageid') 

	argparser.add_argument(
		"-verbose", action='store_true', help="Enable detailed log")

	argparser.add_argument(
		"-debug", action='store_true', help="Enable Debugging mode")

	args = argparser.parse_args()
	# print(args)
	Logging.debug=args.debug
	## used filter to remove empty contents from list


	Confluence(
	 pageid=args.pageid,
	)
