#! /usr/bin/env python

# %%

from cgitb import lookup
import sys,os
import logging
import re
import pprint
import json
import msal
import requests
import  atexit
import urllib.parse
import argparse
import datetime as dt
from Shared import Logging,DebugMsg,DebugMsg2,Info,Shared,bold,boldr
import  zipfile, io
from tika import parser
try:
	from xml.etree.cElementTree import XML
except ImportError:
	from xml.etree.ElementTree import XML

import functools
from concurrent.futures import ThreadPoolExecutor

class SharepointSearch():
	def __init__(self,keywords,credentialsFile=None,
              SearchSharepoint=True, SearchFindit=True,SearchMail=True, SearchTeams=True,
              regexs=[],getregexs=[],max_results=50,token=None):
		self.max_results=max_results
		defaultsFile = Shared.defaultsFilePath
		credentialsHead = "Sharepoint"
		self.__get_regexs=getregexs
		self.regexs=regexs
#		SearchSharepoint=False
#		SearchFindit=False
#		SearchMail=False
#		SearchTeams=False
		self.token=token
		self.combined_results={}


		self.defaults=Shared.read_defaults(defaultsFile,credentialsHead)

		self.config={}
		self.config["endpoints"]={
			"sharepoint": self.defaults['EndPoint'],
			"findit" : self.defaults['Findit']['EndPoint']
		}
		self.token_info={}
		if self.token is not None:
			self.token_info['access_token']=self.token
		else:	
			if credentialsFile is None:
				credentialsFile = self.defaults["CredentialsFile"]
			self.tokenCacheFile=Shared.abs_path(credentialsFile)
			self.credentials=Shared.read_credentials(credentialsFile,credentialsHead)
			self.config["authority"]= "https://login.microsoftonline.com/" + self.credentials['tenant_id']  
			self.config["client_id"]= self.credentials['client_id']
			self.setTokenCache()
		
		self.keywords=keywords
		keywords=self.combine_keywords(keywords)
		self.share_point_scopes=self.defaults['Scopes']
		self.findit_scopes=self.defaults['Findit']['Scopes']
		if SearchSharepoint:
			DebugMsg("Search Sharepoint")
			results=self.get_results_tp(scope=self.share_point_scopes,keywords=keywords,search_func=self.search_sharepoint)
			self.get_matching_results_tp("Sharepoint", results,regexs,search_regex_func=self.search_regexp_sharepoint,print_results_func=self.printResultsSharepoint)

		if SearchFindit:
			DebugMsg("Search findit")
			results=self.search_findit(scope=self.findit_scopes, keywords=keywords)
			header="Wiki results matching the search query"
			self.printResults(results,header,print_results_func=self.printResultsFindit)
			self.combined_results["Wiki"]={}
			self.combined_results["Wiki"]['Matched']=[]
			self.combined_results["Wiki"]['Unmatched']=[]
			for result in results:
				self.combined_results["Wiki"]['Matched'].append({ "Subject" : result, 'Summary' : '' , 'Link' : result})

		if SearchMail:
			DebugMsg("Search Mail")
#			self.search_mail(scope=["Sites.Read.All"], keywords=keywords)
			results=self.get_results_tp(scope=self.share_point_scopes,keywords=keywords,search_func=self.search_mail)
			self.get_matching_results_tp("Email", results,regexs,search_regex_func=self.search_regexp_mail,print_results_func=self.printResultsMail)

		if SearchTeams:
			DebugMsg("Search Teams")
#			self.search_mail(scope=["Sites.Read.All"], keywords=keywords)
			results=self.get_results_tp(scope=self.share_point_scopes,keywords=keywords,search_func=self.search_chat)
			self.get_matching_results_tp("Chat", results,regexs,search_regex_func=self.search_regexp_teams,print_results_func=self.printResultsTeams)
	
 
	def get_results(self):
		print(self.combined_results)
		return self.combined_results

	
	
	
	def combine_keywords(self,keywords):
		tmp=[]
		for keyword in keywords:
			tmp.append("\"" + keyword + "\"")
		return " ".join(tmp)

	


	def setTokenCache(self):
		self.__cache= msal.SerializableTokenCache()
		if os.path.exists(self.tokenCacheFile):
			js=Shared.read_credentials_File(self.tokenCacheFile)
			if "token_cache" in js:
				DebugMsg(f"token cache found ")
				self.__cache.deserialize(js["token_cache"])
			else:
				DebugMsg("token cache not found in credential file")
		atexit.register(self.updateTokenCache)
		

	def updateTokenCache(self,Force=False):
		js={}
		if self.__cache.has_state_changed or Force:
			if os.path.exists(self.tokenCacheFile):
				js=Shared.read_credentials_File(self.tokenCacheFile)

			js["token_cache"]= self.__cache.serialize()
			DebugMsg("Token Cache updated")
			Shared.update_credentials(self.tokenCacheFile,js)
	
	def acquire_token(self,scope):
		if 'access_token' in self.token_info and self.token_info['access_token'] is not None:
			return
		app = msal.PublicClientApplication(
						self.config["client_id"], authority=self.config["authority"],

						token_cache=self.__cache
						)

		self.token_info = None
		accounts = app.get_accounts()
		chosen=None
		if accounts:
			DebugMsg("Pick the account you want to use to proceed:")
			if len(accounts)>1:
				for a in accounts:
					print(a["username"])
			# Assuming the end user chose this one
			chosen = accounts[0]
			DebugMsg(f"Accounts found {chosen}")
			# Now let's try to find a token in cache for this account
			self.token_info  = app.acquire_token_silent(scope, account=chosen)
		else:
			DebugMsg("Accounts not found")

		if not self.token_info :
			DebugMsg(f"No suitable token exists in cache. Let's get a new one from AAD for scope {scope} and account {chosen}")

			flow = app.initiate_device_flow(scopes=scope)
			if "user_code" not in flow:
				raise ValueError(
					"Fail to create device flow. Err: %s" % json.dumps(flow, indent=4))


			print(flow["message"])
			sys.stdout.flush()  # Some terminal needs this to ensure the message is shown
	# Ideally you should wait here, in order to save some unnecessary polling
	# input("Press Enter after signing in from another device to proceed, CTRL+C to abort.")
			self.token_info  = app.acquire_token_by_device_flow(flow)  # By default it will block

		if "access_token" in self.token_info:
			self.updateTokenCache()
		else:
			print(self.token_info.get("error"))
			print(self.token_info.get("error_description"))
			print(self.token_info.get("correlation_id"))  # You may need this when reporting a bug
			raise ValueError("Could not acquire token to run search")

			
	# Hint: The following optional line persists only when state changed

	def search_mail(self,scope,keywords,max_results_per_iter=10,start_at=0):
		self.acquire_token(self.share_point_scopes)   ##  this will update the token info
		headers={'Authorization': 'Bearer ' + self.token_info['access_token'],
		"Content-Type" : "application/json"
		}

		params=None
		data={
			"requests": [
				{
					"entityTypes": [
						"message"
					],
					"query": {
						"queryString": keywords 
					},
					"from": start_at,
					"size": max_results_per_iter
				}
			]
		}
					#"fields" : ["parentReference","webUrl"],
		graph_data = requests.post(
			self.config["endpoints"]["sharepoint"],
			headers=headers,
			params=params,
			data=json.dumps(data)
		)
			#data=json.dumps(data)
		content=json.loads(graph_data.content)
	##	pprint.pprint(content)
		results={}
		subjects=set()
		
		if 'value' in content:
			if 'hits' in content['value'][0]['hitsContainers'][0]: 
				for x in content['value'][0]['hitsContainers'][0]['hits']:
					weburl=re.sub(" ","%20",x['resource']['webLink'])
					requests.get(weburl,headers=headers)
					#weburl=weburl.replace("&viewmodel=ReadMessageItem","")

					subject=x['resource']['subject']
					if weburl in results or subject in subjects: 
						DebugMsg("URL %s already exists, not added" % weburl)
					else:
						id=x['hitId']
						url='https://graph.microsoft.com/v1.0/me/messages/' + id + '/$value'
						results[weburl]=[subject,url]
						subjects.add(subject)
		return results
         

	def search_chat(self,scope,keywords,max_results_per_iter=10,start_at=0):
		self.acquire_token(self.share_point_scopes)   ##  this will update the token info
		headers={'Authorization': 'Bearer ' + self.token_info['access_token'],
		"Content-Type" : "application/json"
		}
#		print("###")
	#	print(self.token_info['access_token'])
	#	print("###")

		params=None
		data={
			"requests": [
				{
					"entityTypes": [
						"chatMessage"
					],
					"query": {
						"queryString": keywords 
					},
					"from": start_at,
					"size": max_results_per_iter
				}
			]
		}
					#"fields" : ["parentReference","webUrl"],
		graph_data = requests.post(
			self.config["endpoints"]["sharepoint"],
			headers=headers,
			params=params,
			data=json.dumps(data)
		)
			#data=json.dumps(data)
		content=json.loads(graph_data.content)
		#pprint.pprint(content)
		results={}
		subjects=set()
		DebugMsg(f"Seaching in chat {keywords}")	
		if 'value' in content:
			if 'hits' in content['value'][0]['hitsContainers'][0]: 
				for x in content['value'][0]['hitsContainers'][0]['hits']:
					weburl=re.sub(" ","%20",x['resource']['webLink'])
					requests.get(weburl,headers=headers)
					#weburl=weburl.replace("&viewmodel=ReadMessageItem","")
					subject=''
					if 'subject' in x['resource']:
						subject=x['resource']['subject']
					subject=subject + "\n"+  x['summary']
					subject=re.sub(r'\n\s*\n+', '\n\n', subject)
					subject=re.sub(r'\n', '\n\t', subject)
					if weburl in results or subject in subjects: 
						DebugMsg("URL %s already exists, not added" % weburl)
					else:
						id=x['hitId']
						url='https://graph.microsoft.com/v1.0/me/messages/' + id + '/$value'
						results[weburl]=[subject,url]
						subjects.add(subject)
		return results
         
	def search_sharepoint(self,scope,keywords,max_results_per_iter,start_at):
		self.acquire_token(scope)   ##  this will update the token info
		headers={'Authorization': 'Bearer ' + self.token_info['access_token'],
		"Content-Type" : "application/json"
		}

		params=None
		data={
			"requests": [
				{
					"entityTypes": [
						"driveItem"
					],
					"query": {
						"queryString": keywords + " filetype:docx OR filetype:doc OR filetype:pptx OR filetype:ppt OR filetype:pdf OR filetype:one"
					},
					"sortProperties": [
						{
							"name": "lastModifiedDateTime",
							"isDescending": "true"
						}
					],
					"from": start_at,
					"size": max_results_per_iter
				}
			]
		}
					#"fields" : ["parentReference","webUrl"],
		graph_data = requests.post(
			self.config["endpoints"]["sharepoint"],
			headers=headers,
			params=params,
			data=json.dumps(data)
		)
			#data=json.dumps(data)
		content=json.loads(graph_data.content)
		#pprint.pprint(content)
		results={}
		
		if 'value' in content:
			if 'hits' in content['value'][0]['hitsContainers'][0]: 
				for x in content['value'][0]['hitsContainers'][0]['hits']:
					weburl=re.sub(" ","%20",x['resource']['webUrl'])
					if weburl in results:
						DebugMsg("URL %s already exists, not added" % weburl)
						continue

					driveId=x['resource']['parentReference']['driveId']
					id=x['resource']['parentReference']['id']
					siteId=x['resource']['parentReference']['siteId'].split(",")[1]
					listId=x['resource']['parentReference']['sharepointIds']['listId']
					listItemUId=x['resource']['parentReference']['sharepointIds']['listItemUniqueId']
					listItemId=x['resource']['parentReference']['sharepointIds']['listItemId']
					headers={'Authorization': 'Bearer ' + self.token_info['access_token'],
						'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
						'Accept-Language': 'en-US,en;q=0.9'
					}
					
					url='https://graph.microsoft.com/v1.0/sites/' + siteId + '/lists/' + listId + '/items/' + listItemId + '/driveItem'
#					print(url)
					response = requests.get(url, headers=headers)
					if (response.ok):
						x=json.loads(response.content)
						results[weburl]=x['@microsoft.graph.downloadUrl']
						#print("####################")
					else:
						results[weburl]=None
						#print(weburl)
					#print("####")
		return results
         

	def search_findit(self,scope,keywords):
		self.acquire_token(scope)   ##  this will update the token info

		headers={'Authorization': 'Bearer ' + self.token_info['access_token'],
		"Content-Type" : "application/json"
		}

		url= self.config["endpoints"]["findit"] + "?querytext=" + urllib.parse.quote_plus("'"+ keywords + "'")
		graph_data = requests.get(
			url,
			headers=headers,
		)
			#data=json.dumps(data)
		DebugMsg2(graph_data.content)

#		urls=[]
		results=[]
		if b'xml version=' in graph_data.content:
			returned_urls=re.findall(b"https:.*?<",graph_data.content)
			for url in returned_urls:
				tmp=url.decode("utf-8") 
				#print("##")
				#print(tmp)
				tmp=re.sub("<.*","",tmp)
				tmp=re.sub("\?.*","",tmp)
				if "sharepoint.com" not in tmp and tmp not in results:
					results.append(tmp)
			#if len(urls)>0:
			#	for url in urls:
			#		results.append(url)
#					Info(url,print_dt=False)
		else:
			print(graph_data.content)
		return results




	def get_docx_text(self,document):
		"""
		Take the path of a docx file as argument, return the text in unicode.
		"""
		WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
		PARA = WORD_NAMESPACE + 'p'
		TEXT = WORD_NAMESPACE + 't'
		xml_content = document.read('word/document.xml')
		document.close()
		tree = XML(xml_content)

		paragraphs = []
		for paragraph in tree.iter(PARA):
			texts = [node.text
					for node in paragraph.iter(TEXT)
					if node.text]
			if texts:
				paragraphs.append(''.join(texts))

		return '\n\n'.join(paragraphs)


			#print("Graph API call result: %s" % json.dumps(graph_data, indent=2))

	def get_results_tp(self,scope, keywords,search_func):
		max_results_per_iter=10
		start_ats=[]
		for i in range(0,int(self.max_results/max_results_per_iter)):
			start_ats.append(max_results_per_iter*i)

		max_threads=10
		with ThreadPoolExecutor(max_workers=max_threads) as exe:
			fp=functools.partial(search_func,
									scope, keywords,
									max_results_per_iter)
			results_iters=exe.map(fp,start_ats)

		results_dic={}
		results=[]
	#	print(results_iters)
	#	print(results_dic)
		for results_iter in results_iters:
			results_dic.update(results_iter)

		for result in results_dic:
			results.append([result,results_dic[result]])
		### results will be a list of lists, where each element has webUrl : download Url
			
		DebugMsg("Number of results : " + str(search_func) + str(len(results)))
		return results

	def __search_regexp_tp(self,regexs,search_regex_func,matched_results,not_matched_results,other_info,result):
		#with self.__sema:
		DebugMsg2( "Thread Started = " )
		if search_regex_func(result,regexs):
			matched_results.append(result)
		else:
			not_matched_results.append(result)
		

	def get_matching_results_tp(self,source,results,regexs,search_regex_func,print_results_func):
		matched_results=[]
		not_matched_results=[]
		max_threads=10
		DebugMsg("get_matching_results_tp %d" % len(results))
		with ThreadPoolExecutor(max_workers=max_threads) as exe:
			fp=functools.partial(self.__search_regexp_tp,
									regexs,
									search_regex_func,
									matched_results,
									not_matched_results,
									{'thread':'??'})
			exe.map(fp,results)
		self.__printresults(source,results,matched_results,not_matched_results,print_results_func)
		self.update_results_json(source,matched_results,"Matched")
		self.update_results_json(source,not_matched_results,"NotMatched")


	def update_results_json(self,source,results,subcategory):
		if source not in self.combined_results:
			self.combined_results[source]={}
		if subcategory not in  self.combined_results[source]:
			self.combined_results[source][subcategory]=[]
		for result in results:
			if source == "Sharepoint":
				self.combined_results[source][subcategory].append({ "Subject" : self.get_sharepoint_display(result[0]), 'Summary' : "", 'Link' : result[0]})
			elif (source == "Email") or (source == "Chat"):
				self.combined_results[source][subcategory].append({ "Subject" : result[1][0], 'Summary' : "" , 'Link' : result[0]})
			

	def __printresults(self,source,results,matched_results,not_matched_results,print_results_func):
		DebugMsg("print_results len_matched_results=%d len_unmatched_results=%d" % (len(matched_results),len(not_matched_results)))
		header=""

		if len(matched_results)>0 :
			if len(not_matched_results)>0 and len(matched_results)< 5:
				header=source + " Results from the native search query"
		elif len(results)>0:
			header=source + " Results from the native search query"

		if len(matched_results)< Shared.matched_to_omit:
			self.printResults(not_matched_results,header,print_results_func)
		
		if len(matched_results)>0:
			header="Filtered " + source +  " results exactly matching the search query"
			self.printResults(matched_results,header,print_results_func)



	def printResults(self,results,header,print_results_func):
		if len(results)>0:
			results=results.copy()
			results.reverse
			DebugMsg("\n\n################## Results ###################################",print_dt=False)
			Info(boldr("\n################## " + header + " " + "###################################"),print_dt=False)
			i=0
			for result in results:
				i+=1
				print_results_func(i,  result)

			DebugMsg("################## Results Ends ###################################\n\n",print_dt=False)
			sys.stdout.flush()

	def printResultsMail(self,i,result):
		Info(str(i) + ") " + bold(result[1][0]) + " -- Link --> " + result[0],print_dt=False)

	def printResultsTeams(self,i,result):
		Info(str(i) + ") " + bold(result[0]) + "\n\t "+ result[1][0] + "\n---------------------------" ,print_dt=False)

	def printResultsSharepoint(self,i,result):
			Info(str(i) + ") " + bold(self.get_sharepoint_display(result[0])) + " -- Link -->  " + result[0],print_dt=False)
	
	def get_sharepoint_display(self,result):
		res=re.sub(".*\/","",result)
		res=re.sub("%20"," ",res)
		return res
		

	def printResultsFindit(self,i,result):
			Info(str(i) + ") " + result,print_dt=False)

	def search_regexp_teams(self,result,regexs):
		 ## if downloadurl is none, return false
		headers={'Authorization': 'Bearer ' + self.token_info['access_token'],
		"Content-Type" : "application/json"
		}

		DebugMsg2("search_regexp_teams Regexes %s" % str(regexs))
		if result[1] is None: 
			return False

		#pprint.pprint(result)
		## keywords is added only if some keywords has more than one word
		keywords=[]
		for keyword in self.keywords:
			keyword=keyword.strip()
			if re.search("\s",keyword) or re.search("\W",keyword):
				keywords.append(keyword)

		found=False
		DebugMsg("search_regexp_teams Finding Regexes in Chat")
		if len(self.__get_regexs + regexs + keywords )> 0:
			found=False
#			print(result[1][1])
			
			r= requests.get(result[1][1], headers=headers)
			parsed = parser.from_buffer(r.content)
			#print(parsed["content"]) # To get the content of the file

			for pattern in self.__get_regexs:
				#            DebugMsg("Pattern", pattern)
				found=False
				
				s1=re.search(pattern,parsed["content"],re.IGNORECASE)
				if s1:
					DebugMsg(result[0],s1.group(0))


			for pattern in (regexs + keywords):
				found=False
				if re.search(pattern,parsed["content"],re.IGNORECASE):
					found=True
				if not found:
					return False
		return found


	def search_regexp_mail(self,result,regexs):
		 ## if downloadurl is none, return false
		headers={'Authorization': 'Bearer ' + self.token_info['access_token'],
		"Content-Type" : "application/json"
		}

		DebugMsg2("Regexes %s" % str(regexs))
		if result[1] is None: 
			return False

		## keywords is added only if some keywords has more than one word
		keywords=[]
		for keyword in self.keywords:
			keyword=keyword.strip()
			if re.search("\s",keyword) or re.search("\W",keyword):
				keywords.append(keyword)

		found=False
		DebugMsg("Finding Regexes in Mail")
		if len(self.__get_regexs + regexs + keywords )> 0:
			found=False
#			print(result[1][1])
			r= requests.get(result[1][1], headers=headers)
			parsed = parser.from_buffer(r.content)
			#print(parsed["content"]) # To get the content of the file

			for pattern in self.__get_regexs:
				#            DebugMsg("Pattern", pattern)
				found=False
				
				s1=re.search(pattern,parsed["content"],re.IGNORECASE)
				if s1:
					DebugMsg(result[0],s1.group(0))


			for pattern in (regexs + keywords):
				found=False
				if re.search(pattern,parsed["content"],re.IGNORECASE):
					found=True
				if not found:
					return False
		return found

	def search_regexp_sharepoint(self,result,regexs):
		 ## if downloadurl is none, return false
		if result[1] is None: 
			return False

		## keywords is added only if some keywords has more than one word
		keywords=[]
		for keyword in self.keywords:
			keyword=keyword.strip()
			if re.search("\s",keyword) or re.search("\W",keyword):
				keywords.append(keyword)

		found=False
		DebugMsg("Finding Regexes %s" % str(regexs))
		if len(self.__get_regexs + regexs + keywords )> 0:
			found=False
			r = requests.get(result[1])   ## download url
			parsed = parser.from_buffer(r.content)
			#print(parsed["content"]) # To get the content of the file

			for pattern in self.__get_regexs:
				#            DebugMsg("Pattern", pattern)
				found=False
				s1=re.search(pattern,parsed["content"],re.IGNORECASE)
				if s1:
					DebugMsg(result[0],s1.group(0))


			for pattern in (regexs + keywords):
				found=False
				if re.search(pattern,parsed["content"],re.IGNORECASE):
					found=True
				if not found:
					return False
		return found


if __name__ == "__main__":

	argparser = argparse.ArgumentParser(description="SharepointSearch")
	argparser.add_argument('keywords', nargs='+')
	argparser.add_argument('-credentialsFile', default=None)
	argparser.add_argument(
		"-regex", metavar="regex", required=False, help="DashboardDataDir",nargs='+', default=[])

	argparser.add_argument(
		"-getregex", metavar="regex", required=False, help="DashboardDataDir",nargs='+', default=[])

	argparser.add_argument(
		"-verbose", action='store_true', help="Enable detailed log")

	argparser.add_argument(
		"-debug", action='store_true', help="Enable Debugging mode")

	args = argparser.parse_args()
	# print(args)
	Logging.debug=args.debug
	token='eyJ0eXAiOiJKV1QiLCJub25jZSI6IlhLMEdUWFVZZ1NFVGxHeVB3a001Y2VDcG44U0NmQU1ENklhNjFPeC1aU2MiLCJhbGciOiJSUzI1NiIsIng1dCI6Ii1LSTNROW5OUjdiUm9meG1lWm9YcWJIWkdldyIsImtpZCI6Ii1LSTNROW5OUjdiUm9meG1lWm9YcWJIWkdldyJ9.eyJhdWQiOiIwMDAwMDAwMy0wMDAwLTAwMDAtYzAwMC0wMDAwMDAwMDAwMDAiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9mMzRlNTk3OS01N2Q5LTRhYWEtYWQ0ZC1iMTIyYTY2MjE4NGQvIiwiaWF0IjoxNjkzNjc2NDU1LCJuYmYiOjE2OTM2NzY0NTUsImV4cCI6MTY5MzY4MjA0NiwiYWNjdCI6MCwiYWNyIjoiMSIsImFpbyI6IkFUUUF5LzhVQUFBQThFLzc2M0JKeEVIcGtMQ2VWNnpuYnNyQkNtWnc4WWx4b1ZDSzQwemtwRU13YjBoQ2ticVdKdG9NbDAvVTRlOVIiLCJhbXIiOlsicHdkIl0sImFwcF9kaXNwbGF5bmFtZSI6IlVuaVNlYXJjaCIsImFwcGlkIjoiZDRkYWM2NDAtNzU0YS00N2I1LTk3ZmYtNWMxMjUyZjgzODZhIiwiYXBwaWRhY3IiOiIwIiwiZmFtaWx5X25hbWUiOiJKaW5kYWwiLCJnaXZlbl9uYW1lIjoiTml0aW4iLCJpZHR5cCI6InVzZXIiLCJpcGFkZHIiOiIyMTcuMTQwLjEwMi4xMyIsIm5hbWUiOiJOaXRpbiBKaW5kYWwiLCJvaWQiOiJkY2Q5ZWYyNS00MGZmLTQ1ZWQtODNhZi1iZDcyNjM1YjI0ZTUiLCJvbnByZW1fc2lkIjoiUy0xLTUtMjEtMTcxNTU2NzgyMS0xNjQ0NDkxOTM3LTcyNTM0NTU0My0xMTI4NzIiLCJwbGF0ZiI6IjgiLCJwdWlkIjoiMTAwMzAwMDA5MTY2RDZGMCIsInJoIjoiMC5BUkFBZVZsTzg5bFhxa3F0VGJFaXBtSVlUUU1BQUFBQUFBQUF3QUFBQUFBQUFBQVFBSFEuIiwic2NwIjoiQWxsU2l0ZXMuTWFuYWdlIEFsbFNpdGVzLlJlYWQgQ2FsZW5kYXJzLlJlYWQgQ2FsZW5kYXJzLlJlYWQuU2hhcmVkIENhbGVuZGFycy5SZWFkV3JpdGUgQ2hhbm5lbE1lc3NhZ2UuUmVhZC5BbGwgQ2hhdC5DcmVhdGUgQ2hhdC5SZWFkIENoYXQuUmVhZEJhc2ljIENoYXQuUmVhZFdyaXRlIENoYXRNZXNzYWdlLlJlYWQgQ2hhdE1lc3NhZ2UuU2VuZCBlbWFpbCBGaWxlcy5SZWFkIEZpbGVzLlJlYWQuQWxsIEZpbGVzLlJlYWQuU2VsZWN0ZWQgRmlsZXMuUmVhZFdyaXRlLkFsbCBNYWlsLlJlYWQgTWFpbC5SZWFkLlNoYXJlZCBNYWlsLlJlYWRCYXNpYyBNYWlsLlJlYWRXcml0ZSBNYWlsLlNlbmQgTXlGaWxlcy5SZWFkIG9wZW5pZCBwcm9maWxlIFByb2plY3QuUmVhZCBTaXRlcy5NYW5hZ2UuQWxsIFNpdGVzLlJlYWQuQWxsIFNpdGVzLlJlYWRXcml0ZS5BbGwgVGVhbS5DcmVhdGUgVGVhbS5SZWFkQmFzaWMuQWxsIFVzZXIuUmVhZCBVc2VyLlJlYWRCYXNpYy5BbGwiLCJzaWduaW5fc3RhdGUiOlsiaW5rbm93bm50d2siLCJrbXNpIl0sInN1YiI6IjNlTE8yN1h1YzBFRjRWNHpxMnVjRHZyZGVQUzd6UGtIRXdwZlRyRzNvRG8iLCJ0ZW5hbnRfcmVnaW9uX3Njb3BlIjoiRVUiLCJ0aWQiOiJmMzRlNTk3OS01N2Q5LTRhYWEtYWQ0ZC1iMTIyYTY2MjE4NGQiLCJ1bmlxdWVfbmFtZSI6Ik5pdGluLkppbmRhbEBhcm0uY29tIiwidXBuIjoiTml0aW4uSmluZGFsQGFybS5jb20iLCJ1dGkiOiIyNzh6UWlTWWZFMnhnZF9HZVp0b0FBIiwidmVyIjoiMS4wIiwid2lkcyI6WyJiNzlmYmY0ZC0zZWY5LTQ2ODktODE0My03NmIxOTRlODU1MDkiXSwieG1zX3N0Ijp7InN1YiI6IjBMNWZaZ0xQVGRvOEZXVEl2eU5FYjhXb3I3YUlKWlZzbF95UFBiak43Sk0ifSwieG1zX3RjZHQiOjE0Mjk3MTM5NTR9.RQvwLiMd38fpKJPuKu8oEyOG9tmg0dBQyQgHlagL8fcaYIajd35dGQ114wTr9aG2ebPWgdp62qU6K4XpbQNos2IHm052mVm5SHfrcF0J1fQc-QSnsEwF5P4W8zLxtylQKS92qzTt7bwDDwfvFsre-RA6_b9aq3bp2dJKhSIrry_3ejzQeCUbJXhiNL_6N221axWb7i9WYYera9ONxZsq2YcHf-ebbdN0smflgQDV9wYTyCx3MtIgqSLS-l4r6-pbg5OPdYEHm7M9ur2KBOte6xFrWsjIYWkWMmpHAbuFikuQZDOoen5nQPOSO8JYNyEWATwYCl5pglghEMMQKmMQ3w'
	x=SharepointSearch(keywords=args.keywords,token=token)
	x1=x.get_results()


# %%
