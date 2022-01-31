#! /usr/bin/env python
#
# %%
import sys
import os
import re
import argparse
import json
import urllib.parse
import Shared


import datetime as dt
import atlassian 
from Shared import Logging,DebugMsg,Info,Shared

# %%
#confluence.get_all_spaces(start=0, limit=5, expand=None)
#confluence.get_space("PDG", expand='description.plain,homepage')
##confluence.create_page("PDG", "FAQ test", "test1", parent_id=143032322, type='page', representation='storage', editor='v2')
##confluence.create_page("PDG", "Page1", "test", parent_id=PageId_test1, type='page', representation='storage', editor='v2')
#
#heading="Pegasus Execution Flow"
#
##paragraph='''
#
#In this paragraph the Pegasus execution flow will be explained using as an example the "mst target", but it is common for most Pegasus targets.
#The Pegasus command to lunch the mst target is:
#mmake mst CELLS=Cell1
#The result is shown in Fig. 3. The mmake script is going to call the $PEGASUS_PATH/mem/bin/mmake variables which reads three main files. Those files must be present in the directory in which you are lunching the Pegasus target.
#If you have sight problem like Astigmatism, presbyopia or daltonism, it is difficult to understand what it is written in orange/white bold character.
#You might use just bold white character to highlight the example. It is a little bit difficult to understand what you wanted to express by $PEGASUS_PATH/mem/makefiles
#$PEGASUS_SP_PATH/<hot_fix/enhancements> when you do not know what it is it.. like reas is going to look for the variables called $PEGASUS_PATH/mem/makefiles
#$PEGASUS_SP_PATH/<hot_fix/enhancements??
#And then after it look for it it writes a wrapper?
#
#'''
#
##space="PDG"
##PageId_Memory_Workflows=577227622
##PageId_FAQs=924951844
##PageId_test1=924952128
##page_body="<br /><h1>" + heading + "</h1><p>" +  htmlspecialchars(paragraph.strip()) + "</p>" 
##page_title=confluence.get_page_by_id( PageId_test1, expand=None, status=None, version=None)['title']
#print(page_title)
#confluence.append_page(PageId_test1, page_title ,page_body, parent_id=PageId_FAQs, type='page', representation='storage', minor_edit=False)
#confluence.get_page_by_title(space, "FAQ test", start=None, limit=None)

#%%
#confluence.update_page(space, title, start=None, limit=None)
# %%
class AddFaqConfluence:

	def __init__(self, heading,paragraph,credentialsFile=None,credentialsHead=None):

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
		self.appendInFAQs(heading=heading,paragraph=paragraph)


	  #  self.get_matching_results(results,regexs)

	def appendInFAQs(self,heading,paragraph):
		heading=" ".join(heading)
		paragraph=" ".join(paragraph)
		PageId_Memory_Workflows=577227622
		PageId_FAQs=924951844
		PageId_test1=924952128
		page_body="<br /><h1>" + self.htmlspecialchars(heading.strip())+ "</h1><p>" +  self.htmlspecialchars(paragraph.strip()) + "</p>" 
		if not Shared.isVpnConnected(self.credentials["server"]):
			return
		page_info=self.confluence.get_page_by_id( PageId_test1, expand=None, status=None, version=None)
		page_url=self.credentials["server"] + page_info['space']['_links']['webui']  + "/" + urllib.parse.quote_plus( page_info['title'] )
		page_title=page_info['title']
		added=self.confluence.append_page(PageId_test1, page_title ,page_body, parent_id=PageId_FAQs, type='page', representation='storage', minor_edit=False)
		if 'id' in added:
			Info("Appended in " + page_url)
		return added

	def htmlspecialchars(self,text):
		return (
			text.replace("&", "&amp;").
			replace('"', "&quot;").
			replace("<", "&lt;").
			replace(">", "&gt;").
			replace("\n","<br />")
		)
	


if __name__ == "__main__":

	argparser = argparse.ArgumentParser(description="Confluence Search")
	argparser.add_argument('-heading', nargs='+')
	argparser.add_argument('-paragraph', nargs='+')

	argparser.add_argument(
		"-verbose", action='store_true', help="Enable detailed log")


	argparser.add_argument(
		"-debug", action='store_true', help="Enable Debugging mode")


	args = argparser.parse_args()


	AddFaqConfluence(heading=args.heading,paragraph=args.paragraph, credentialsFile="~/.UniSearch.json")
