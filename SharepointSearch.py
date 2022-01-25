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
from Shared import Logging,DebugMsg,Info


class SharepointSearch():
    def __init__(self,keywords,credentialsFile=None,SearchSharepoint=True,SearchFindit=True):
        if credentialsFile is None:
            credentialsFile= "~/.SharePointSearch.json"
        self.tokenCacheFile=os.path.abspath(os.path.expanduser(os.path.expandvars(credentialsFile)))
        self.read_credentials(self.tokenCacheFile)
        self.define_configs()
        self.setTokenCache()
        atexit.register(self.updateTokenCache)
        keywords=self.combine_keywords(keywords)
        if SearchSharepoint:
            self.search_sharepoint(scope=["Sites.Read.All"],keywords=keywords)
        if SearchFindit:
            self.search_findit(scope=["https://armh.sharepoint.com/Sites.Read.All"], keywords=keywords)
    
    def combine_keywords(self,keywords):
        tmp=[]
        for keyword in keywords:
            tmp.append("\"" + keyword + "\"")
        return " ".join(tmp)

    
    def define_configs(self):
        self.config={

                                "authority": "https://login.microsoftonline.com/" + self.tenant_id  ,
                                "client_id": self.client_id,
                                }
#        "scope": ["Sites.Read.All", "https://armh.sharepoint.com/Sites.Read.All"]

        self.config["endpoints"]={
            "sharepoint": "https://graph.microsoft.com/v1.0/search/query",
            "findit" : "https://armh.sharepoint.com/_api/search/query"
        }


    def read_credentials(self,credentialsFile):
        if os.path.exists(credentialsFile):
            with open (credentialsFile) as o:
                creds=json.load(o)
            self.client_id=creds['MicrosoftCredentials']['client_id']
            #self.client_secret=creds['MicrosoftCredentials']['client_secret']
            self.tenant_id=creds['MicrosoftCredentials']['tenant_id']
        else:
            DebugMsg("Credentials File %s does not exist" % credentialsFile)

    def setTokenCache(self):
        self.__cache= msal.SerializableTokenCache()
        if os.path.exists(self.tokenCacheFile):
            with open(self.tokenCacheFile) as f:
                js=json.load(f)
                if "token_cache" in js:
                    self.__cache.deserialize(js["token_cache"])
        

    def updateTokenCache(self):
        js={}

        if self.__cache.has_state_changed:
            if os.path.exists(self.tokenCacheFile):
                with open(self.tokenCacheFile) as f:
                    js=json.load(f)

            js["token_cache"]= self.__cache.serialize()
        
            with open(self.tokenCacheFile,"w") as f:
                json.dump(js,f)
    
    def acquire_token(self,scope):
        app = msal.PublicClientApplication(
                        self.config["client_id"], authority=self.config["authority"],

                        token_cache=self.__cache
                        )

        self.token_info = None
        accounts = app.get_accounts()
        if accounts:
#            print("Pick the account you want to use to proceed:")
            if len(accounts)>1:
                for a in accounts:
                    print(a["username"])
            # Assuming the end user chose this one
            chosen = accounts[0]
            # Now let's try to find a token in cache for this account
            self.token_info  = app.acquire_token_silent(scope, account=chosen)

        if not self.token_info :
            DebugMsg("No suitable token exists in cache. Let's get a new one from AAD.")

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

    def search_sharepoint(self,scope,keywords):
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
                        "queryString": keywords + " filetype:docx OR filetype:doc OR filetype:pptx OR filetype:ppt"
                    },
                    "sortProperties": [
                        {
                            "name": "lastModifiedDateTime",
                            "isDescending": "true"
                        }
                    ],
                    "fields" : ["webUrl"],
                    "from": 0,
                    "size": 50
                }
            ]
        }
        #headers={'Authorization': 'Bearer ' + result['access_token']},
            # Calling graph using the access token
                # Use token to call downstream service
        graph_data = requests.post(
            self.config["endpoints"]["sharepoint"],
            headers=headers,
            params=params,
            data=json.dumps(data)
        )
            #data=json.dumps(data)
        content=json.loads(graph_data.content)
#        pprint.pprint(content)
        if 'value' in content:
            if 'hits' in content['value'][0]['hitsContainers'][0]: 
                for x in content['value'][0]['hitsContainers'][0]['hits']:
                    print(re.sub(" ","%20",x['resource']['webUrl']))
        else:
            print(content)

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

        urls=[]
        if b'xml version=' in graph_data.content:
            returned_urls=re.findall(b"https:.*?<",graph_data.content)
            for url in returned_urls:
                tmp=url.decode("utf-8") 
                #print("##")
                #print(tmp)
                tmp=re.sub("<.*","",tmp)
                tmp=re.sub("\?.*","",tmp)
                if "sharepoint.com" not in tmp and tmp not in urls:
                    urls.append(tmp)
            if len(urls)>0:
                for url in urls:
                    Info(url,print_dt=False)
        else:
            print(graph_data.content)

    def search_findit_org(self,scope,keywords):
        self.acquire_token(scope)   ##  this will update the token info

        headers={'Authorization': 'Bearer ' + self.token_info['access_token'],
        "Content-Type" : "application/json"
        }
        params = (
            ('querytext', keywords),
        )
        #params = (
        #    ('querytext', '\'ESPCV\''),
        #)
        data=json.dumps(
                {
                    "requests": [
                        {
                            "entityTypes": [
                                "driveItem"
                            ],
                            "query": {
                                "queryString": keywords
                            },
                            "from": 0,
                            "size": 20
                        }
                    ]
                }
            )
        data=None
        #headers={'Authorization': 'Bearer ' + result['access_token']},
            # Calling graph using the access token
                # Use token to call downstream service
        graph_data = requests.get(
            self.config["endpoints"]["findit"],
            headers=headers,
            params=params,
            data=data
        )
            #data=json.dumps(data)

        urls=[]
        returned_urls=re.findall(b"<d:Value>https:.*?<",graph_data.content)
        for url in returned_urls:
            tmp=url.decode("utf-8") 
            print("####1")
            pprint.pprint(tmp)
            tmp=re.sub("^<d:Value>","",tmp)
            tmp=re.sub("\s.*","",tmp)
            print("####2")
            pprint.pprint(tmp)
            tmp=re.sub("<.*","",tmp)
            print("####3")
            pprint.pprint(tmp)
            tmp=re.sub("\?.*","",tmp)
            print("####4")
            pprint.pprint( tmp)
            print("####5")
            if "sharepoint.com" not in tmp and tmp not in urls and "http" in tmp:
                urls.append(tmp)
        if len(urls)>0:
            pprint.pprint(urls)
        else:
            print(graph_data.content)
        sys.stdout.flush()

            #print("Graph API call result: %s" % json.dumps(graph_data, indent=2))


if __name__ == "__main__":

    argparser = argparse.ArgumentParser(description="Jira")
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
    SharepointSearch(keywords=args.keywords,credentialsFile=args.credentialsFile)


# %%
