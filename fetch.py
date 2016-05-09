
# -*- coding: utf-8 -*-
'''

@author: ailete619
'''
from ailete619.beakon.handlers import AdminHandler, InternalHandler
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import logging
import urllib

encoding_list = [
                 "shift_jis",
                 "shift_jis_2004",
                 "shift_jisx0213",
                 "ascii",
                 "big5",
                 "big5hkscs",
                 "cp037",
                 "cp424",
                 "cp437",
                 "cp500",
                 "cp720",
                 "cp737",
                 "cp775",
                 "cp850",
                 "cp852",
                 "cp855",
                 "cp856",
                 "cp857",
                 "cp858",
                 "cp860",
                 "cp861",
                 "cp862",
                 "cp863",
                 "cp864",
                 "cp865",
                 "cp866",
                 "cp869",
                 "cp874",
                 "cp875",
                 "cp932",
                 "cp949",
                 "cp950",
                 "cp1006",
                 "cp1026",
                 "cp1140",
                 "cp1250",
                 "cp1251",
                 "cp1252",
                 "cp1253",
                 "cp1254",
                 "cp1255",
                 "cp1256",
                 "cp1257",
                 "cp1258",
                 "euc_jp",
                 "euc_jis_2004",
                 "euc_jisx0213",
                 "euc_kr",
                 "gb2312",
                 "gbk",
                 "gb18030",
                 "hz",
                 "iso2022_jp",
                 "iso2022_jp_1",
                 "iso2022_jp_2",
                 "iso2022_jp_2004",
                 "iso2022_jp_3",
                 "iso2022_jp_ext",
                 "iso2022_kr",
                 "latin_1",
                 "iso8859_2",
                 "iso8859_3",
                 "iso8859_4",
                 "iso8859_5",
                 "iso8859_6",
                 "iso8859_7",
                 "iso8859_8",
                 "iso8859_9",
                 "iso8859_10",
                 "iso8859_13",
                 "iso8859_14",
                 "iso8859_15",
                 "iso8859_16",
                 "johab",
                 "koi8_r",
                 "koi8_u",
                 "mac_cyrillic",
                 "mac_greek",
                 "mac_iceland",
                 "mac_latin2",
                 "mac_roman",
                 "mac_turkish",
                 "ptcp154",
                 "shift_jis",
                 "shift_jis_2004",
                 "shift_jisx0213",
                 "utf_32",
                 "utf_32_be",
                 "utf_32_le",
                 "utf_16",
                 "utf_16_be",
                 "utf_16_le",
                 "utf_7",
                 "utf_8",
                 "utf_8_sig"]

class CachedPage(ndb.Model):
    headers = ndb.TextProperty()
    source = ndb.TextProperty()

class Handler(InternalHandler):
    @classmethod
    def fetch(self, url, data=None, method=urlfetch.GET, headers=None):
        http_headers = {'Content-Type': 'application/x-www-form-urlencoded','User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36'}
        if headers:
            http_headers.update(headers)
        url_encoded_data = None
        if data:
            url_encoded_data = urllib.urlencode(data)
            method = self.request.get("method")
            if (method and method=="POST") or data:
                return urlfetch.fetch(url=url,payload=url_encoded_data,method=urlfetch.POST,headers=http_headers)
            else:
                url+="?"+url_encoded_data
        return urlfetch.fetch(url=url,method=urlfetch.GET,headers=http_headers)
    def get(self):
        url = self.request.get("url")
        option = self.request.get("option")
        logging.info("Fetch: option="+option)
        encoding = self.request.get("encoding")
        logging.info("Fetch: encoding="+encoding)
        if url:
            if option=="cache":
                cached_page = CachedPage.get_by_id(url)
                if cached_page:
                    self.response.write(cached_page.source)
                    return
            response = self.fetch(url=url,data=self.request.get("data"),method=self.request.get("method"),headers=self.request.get("headers"))
            if response.status_code==200:
                try:
                    source = response.content.decode(encoding)#.encode('utf_8').decode('unicode-escape')
                except UnicodeDecodeError:
                    for encoding in encoding_list:
                        try:
                            source = response.content.decode(encoding)#.encode('utf_8').decode('unicode-escape')
                            break
                        except UnicodeDecodeError:
                            pass
                        
                if option!="no_cache":
                    cached_page = CachedPage(id=url,source=source,headers=str(response.headers))
                    cached_page.put()
                self.response.out.write(source)
            else:
                self.error(response.status_code)
                self.response.out.write(response.content)
        else:
            self.abort(404)

class CacheDeleteHandler(AdminHandler):
    def get(self,**kwargs):
        self.render_response('cache-delete.html')
    def post(self,**kwargs):
        delete_url = self.request.get("deleteURL")
        cached_page = CachedPage.get_by_id(delete_url)
        if cached_page:
            cached_page.key.delete()
            self.context["message"] = "deleted"
        else:
            self.context["message"] = "not_found"
        self.render_response('cache-delete.html')
        
class TestHandler(AdminHandler):
    def get(self,**kwargs):
        self.render_response('fetch-test.html')
    def post(self,**kwargs):
        fetch_url = self.request.get("fetchURL")
        fetch_option = self.request.get("fetchOption")
        fetch_encoding = self.request.get("fetchOption")
        url_encoded_data = urllib.urlencode({"url":fetch_url,"option":fetch_option,"encoding":fetch_encoding})
        response = Handler.fetch(url=("https://"+self.request.host+"/fetch?"+url_encoded_data),method=urlfetch.GET)
        self.context["url"] = fetch_url
        self.context["js"] = {}
        self.context["js"]["fetchOption"] = '"'+fetch_option+'"'
        self.context["js"]["fetchEncoding"] = '"'+fetch_encoding+'"'
        self.context["response"] = response.decode('utf_8')
        self.render_response('fetch-test.html')
        
