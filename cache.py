
# -*- coding: utf-8 -*-
'''

@author: ailete619
'''
import ailete619.beakon.commands
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import logging
import urllib
import urllib2
import urlparse
import webapp2

class CachedPage(ndb.Model):
    headers = ndb.TextProperty()
    source = ndb.TextProperty()
    user = ndb.KeyProperty()

class NoCacheHandler(webapp2.RequestHandler):
    def fetch(self):
        http_headers = {'Content-Type': 'application/x-www-form-urlencoded','User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36'}
        headers = self.request.get("headers")
        if headers:
            http_headers.update(headers)
        data = self.request.get("data")
        url_encoded_data = None
        if data:
            url_encoded_data = urllib.urlencode(data)
        method = self.request.get("method")
        url = self.request.get("url")
        if (method and method=="post") or data:
            method = urlfetch.POST
        else:
            method = urlfetch.GET
            url+="?"+url_encoded_data
            url_encoded_data = None
        return urlfetch.fetch(url=url,payload=url_encoded_data,method=method,headers=http_headers)
    def get(self):
        response = self.fetch()
        if response.status_code==200:
            self.response.out.write(response.content)
        else:
            self.error(response.status_code)
            self.response.out.write(response.content)

class CacheHandler(NoCacheHandler):
    def get(self,**kwargs):
        logging.info("kwargs="+str(kwargs))
        logging.info("body="+self.request.body)
        logging.info("url="+self.request.get("url"))
        url = self.request.get("url")
        if url:
            cached_page = CachedPage.get_by_id(url)
            if cached_page:
                logging.info("cached")
                logging.info(cached_page.source)
                self.response.out.write(cached_page.source)
            else:
                logging.info("not cached")
                response = self.fetch()
                if response.status_code==200:
                    cached_page = CachedPage(id=url,source=response.content)
                    cached_page.put()
                    self.response.out.write(response.content)
                else:
                    self.error(response.status_code)
                    self.response.out.write(response.content)
        else:
            self.error(404)
            self.response.out.write('Page Not Found!')

class CacheDeleteHandler(ailete619.beakon.handlers.BaseHandler):
    def get(self,**kwargs):
        self.render_response('cache-delete.html')
    def post(self,**kwargs):
        fetch_url = self.request.get("fetchURL")
        url_encoded_data = urllib.urlencode({"url":fetch_url})
        self.response.write(urlfetch.fetch(url=("https://"+self.request.host+"/fetch/cache?"+url_encoded_data),method=urlfetch.GET).content)
        
class CacheTestHandler(ailete619.beakon.handlers.BaseHandler):
    def get(self,**kwargs):
        self.render_response('cache-test.html')
    def post(self,**kwargs):
        fetch_url = self.request.get("fetchURL")
        url_encoded_data = urllib.urlencode({"url":fetch_url})
        self.response.write(urlfetch.fetch(url=("https://"+self.request.host+"/fetch/cache?"+url_encoded_data),method=urlfetch.GET).content)
        
