
# -*- coding: utf-8 -*-
'''

@author: ailete619
'''
import ailete619.beakon.commands
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import logging
import urllib

class CachedPage(ndb.Model):
    headers = ndb.TextProperty()
    source = ndb.TextProperty()

class Handler(ailete619.beakon.handlers.BaseHandler):
    def fetch(self):
        http_headers = {'Content-Type': 'application/x-www-form-urlencoded','User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36'}
        headers = self.request.get("headers")
        if headers:
            http_headers.update(headers)
        url = self.request.get("url")
        data = self.request.get("data")
        url_encoded_data = None
        if data:
            url_encoded_data = urllib.urlencode(data)
            method = self.request.get("method")
            if (method and method=="post") or data:
                return urlfetch.fetch(url=url,payload=url_encoded_data,method=urlfetch.POST,headers=http_headers)
            else:
                url+="?"+url_encoded_data
        return urlfetch.fetch(url=url,method=urlfetch.GET,headers=http_headers)
    def get(self,**kwargs):
        url = self.request.get("url")
        logging.info(url)
        option = self.request.get("option")
        logging.info(option)
        if url:
            if option=="cache":
                cached_page = CachedPage.get_by_id(url)
                if cached_page:
                    logging.info("from cache")
                    self.response.out.write(cached_page.source)
                    return
            response = self.fetch()
            if response.status_code==200:
                logging.info("not from cache")
                if option!="no_cache":
                    logging.info("cached")
                    cached_page = CachedPage(id=url,source=response.content)
                    cached_page.put()
                self.response.out.write(response.content)
            else:
                self.error(response.status_code)
                self.response.out.write(response.content)
        else:
            self.error(404)
            self.response.out.write('Page Not Found!')

class CacheDeleteHandler(ailete619.beakon.handlers.UserHandler):
    def get(self,**kwargs):
        self.render_response('cache-delete.html')
    def post(self,**kwargs):
        fetch_url = self.request.get("fetchURL")
        url_encoded_data = urllib.urlencode({"url":fetch_url})
        self.response.write(urlfetch.fetch(url=("https://"+self.request.host+"/fetch/cache?"+url_encoded_data),method=urlfetch.GET).content)
        
class TestHandler(ailete619.beakon.handlers.UserHandler):
    def get(self,**kwargs):
        self.render_response('fetch-test.html')
    def post(self,**kwargs):
        fetch_url = self.request.get("fetchURL")
        fetch_option = self.request.get("fetchOption")
        url_encoded_data = urllib.urlencode({"url":fetch_url,"option":fetch_option})
        response = urlfetch.fetch(url=("https://"+self.request.host+"/fetch?"+url_encoded_data),method=urlfetch.GET).content
        self.context["response"] = response
        logging.info(response)
        self.render_response('fetch-test.html')
        
