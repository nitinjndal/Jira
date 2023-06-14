#! /usr/bin/env python
#

import sys
import requests
import logging
import datetime as dt
import json
import os
import stat

from bs4 import BeautifulSoup
from markdown import markdown
import re
import html2text

import collections
import itertools
import Encrypt
import subprocess as sp
## import shutil
#from sympy import primenu
## import pandas as pd
## import time
## import numpy as np
## import tarfile
## from difflib import SequenceMatcher
## import Common.local_functions as LF


class Logging:
	debug=False
	ConsoleLogFile=None
	

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


def DebugMsg(msg1,msg2="",printmsg=True,ForcePrint=False,print_dt=True,error=False):
	if error:
		print("ERROR: " ,end=": " )
		if Logging.ConsoleLogFile is not None:
			Logging.ConsoleLogFile.write("ERROR: ")
		

	if (Logging.debug or ForcePrint) and printmsg:
		if not (((str(msg1) == "" )or (msg1 is None)) and ((str(msg2) == "") or (msg2 is None))) :
			if print_dt:
				print(dt.datetime.now().strftime("%c"),end=": " )
				if Logging.ConsoleLogFile is not None:
					Logging.ConsoleLogFile.write(dt.datetime.now().strftime("%c") + ": ")
		print(str(msg1).encode('utf-8',errors='ignore').decode('charmap',errors='ignore'),end=" ", flush=True )
		if Logging.ConsoleLogFile is not None:
			Logging.ConsoleLogFile.write(str(msg1).encode('utf-8',errors='ignore').decode('charmap',errors='ignore') + " ")
		if msg2 is not None:
			print(str(msg2).encode('utf-8',errors='ignore').decode('charmap',errors='ignore'), flush=True)
			if Logging.ConsoleLogFile is not None:
				Logging.ConsoleLogFile.write(str(msg2).encode('utf-8',errors='ignore').decode('charmap',errors='ignore') + "\n")
		else:
			print("")
			if Logging.ConsoleLogFile is not None:
				Logging.ConsoleLogFile.write("\n")

		sys.stdout.flush()
		if Logging.ConsoleLogFile is not None:
			Logging.ConsoleLogFile.flush()

	if error:
		sys.exit(1)

def DebugMsg2(msg1,msg2=None,printmsg=True,ForcePrint=False,print_dt=True):
	return ""
	#DebugMsg(msg1,msg2,printmsg,ForcePrint,print_dt)

def DebugMsg3(msg1,msg2=None,printmsg=True,ForcePrint=False,print_dt=True):
	DebugMsg(msg1,msg2,printmsg,ForcePrint,print_dt)

def Info(msg1,msg2=None,printmsg=True,ForcePrint=False,print_dt=True):
	DebugMsg(msg1,msg2,printmsg,True,print_dt)

def Error(msg1,msg2=None,printmsg=True,ForcePrint=False,print_dt=True):
	DebugMsg(msg1,msg2,printmsg,True,print_dt,error=True)

def bold(msg):
    return  "\033[1m" + msg + "\033[0m"

def boldr(msg):
    return  "\033[1;7m" + msg + "\033[0m"

class Shared:
	defaultsFilePath=os.path.dirname(os.path.abspath(__file__)) + "/defaults.json"
	matched_to_omit=5

	def read_credentials_File(filename):
		filename=os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))
		try:
			with open(filename,"r") as f: 
				json.load(f)
			## if loaded correctly
			print("Credential File is not encrypted. Please encrypt it with encryption tool")
			
		except:
			creds=None
			mode = os.stat(filename).st_mode

			if  (mode & stat.S_IRGRP) or (mode & stat.S_IROTH) or (mode & stat.S_IWGRP) or (mode & stat.S_IWOTH):
				print(filename + ' readable by group or other people. Please revoke access of others of file using command\n chmod 600 ' + filename)
				exit()
			creds=Encrypt.read_credentials_File(filename)
			return creds


	def update_credentials(filename,credentials):
		filename=os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))
		creds = Encrypt.write_credentials_File(filename,credentials) 
		return creds

	def updateCredentialsJson(unix_passw=None,conf_token=None,jsondata=None):
	#%%
		if unix_passw is not None:
			jsondata['Jira']['credentials']['token']=unix_passw
		if conf_token is not None:
			jsondata['Confluence']['credentials']['token']=conf_token
		return jsondata

	def getCredentialsJson(username,email,unix_passw,conf_token,defaults):
	#%%
		jsondata = {
			"Jira": {
				"credentials": {
					"server": defaults['JiraServer'],
					"token": unix_passw,
					"username": username
				}
			},
			"Confluence": {
				"credentials": {
					"server": defaults['ConfluenceServer'],
					"token": conf_token,
					"username": email
				}
			},
			"Sharepoint": {
				"credentials": {
					"client_id": defaults['client_id'],
					"tenant_id": defaults['tenant_id'],
				}
			}
		}
		return jsondata

	def CreateCredentialsFile(username,email,unix_passw,confluence_token,defaults,credentialsFile):
		jsondata=Shared.getCredentialsJson(username,email,unix_passw,confluence_token,defaults)
		Encrypt.write_credentials_File(credentialsFile,jsondata)
		
	def read_credentials(filename,credentialsHead):
		filename=os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))
		creds = Shared.read_credentials_File(filename) 
		if creds is not None:
			if credentialsHead in creds: 
				creds=creds[credentialsHead]['credentials']
		return creds

	def validUnixCredentials(username,unix_passw):
		defaults=Shared.read_defaults(Shared.defaultsFilePath,"UniSearch")
		command='ldapwhoami -x -w ' + unix_passw + ' -D uid=' + username + ',ou=' + defaults['Ldapou'] + ',dc=' + defaults['Ldapdc'][0]+ ',dc=' + defaults['Ldapdc'][1] 
		validate_creds = sp.Popen(command.split(), stdout=sp.PIPE, stderr=sp.PIPE)
		#DebugMsg(validate_creds.stderr.read())
		#DebugMsg(validate_creds.stdout.read())

		if "Invalid credentials" in validate_creds.stderr.read().decode('utf-8'):
			return False
		elif username not in validate_creds.stdout.read().decode('utf-8'):
			print("Invalid LDAP Message " + validate_creds.stdout.read().decode('utf-8'))      
			return False
		else:
			return True


	def read_defaults(filename,credentialsHead):
		defaults=None
		filename=os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))
		with open(filename) as f:
			defaults= json.load(f)
			defaults = defaults[credentialsHead]
		return defaults

	def abs_path(filename):
		return os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))

	def isVpnConnected(server):
		rep=requests.get(server)
		if b"Sign in to your account" in rep.content:
			Info("Could not connect to " + server + ". Looks like VPN is not connected. Please connect to VPN and retry")
			return False
		return True
	
	def html_to_plain_text(html_string):
		soup = BeautifulSoup(html_string,features="lxml")
		text=soup.get_text('\n')
		return text

	def html_to_plain_text2(html_string):
		markdown_string=html2text.html2text(html_string)
		#""" Converts a markdown string to plaintext """

		# md -> html -> text since BeautifulSoup can extract text cleanly
		html = markdown(markdown_string)

		# remove code snippets
		html = re.sub(r'<pre>(.*?)</pre>', ' ', html)
		html = re.sub(r'<code>(.*?)</code >', ' ', html)

		# extract text
		soup = BeautifulSoup(html, "html.parser")
		text = ''.join(soup.findAll(text=True))

		return text
	
	def tail(filename, n=10):
		with open(filename) as f:
			return "\n".join(list(collections.deque(f, n)))

	def get_n_lines_after_before(pattern,filename,n=3,line_prefix="",line_suffix="",last_lines=0):
		lines=[]
		retval=""
		start_count=False
		count=n+1
		with open(filename) as f:
			if n > 0 :
				before = collections.deque(maxlen=n)
			for line in f:
				count+=1
				if re.search(pattern,line,flags=re.IGNORECASE) is not None:
					if n > 0 and  count > n:
						count=0
						lines=lines+ list(before)
					elif n==0:
						lines.append(line)
#                    lines.append(line)
				if count < n:
					lines.append(line)
				elif count == n:
					lines.append("####################\n\n")
				if n > 0 :
					before.append(line)
		if last_lines>0 and len(lines) > last_lines*n:
			lines=lines[-1*last_lines*n:]
		for line in lines:
			retval=retval + line_prefix+  str(line).strip() + line_suffix + "\n"
		return retval
