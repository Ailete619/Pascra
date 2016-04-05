# -*- coding: utf-8 -*-

import ailete619.beakon.handlers
from fetch import CachedPage
from google.appengine.api import taskqueue
from google.appengine.api import urlfetch
from google.appengine.ext import deferred
from google.appengine.runtime import DeadlineExceededError
import json
import logging
from lxml import etree
from lxml.cssselect import CSSSelector
from lxml.html import parse, fromstring
import re
import urllib
import urllib2
import urlparse
import webapp2
from webapp2_extras import jinja2

class BaseHandler(webapp2.RequestHandler):
    def get(self,**kwargs):
        pass
    @webapp2.cached_property
    def jinja2(self):
        """ Returns a Jinja2 renderer cached in the app registry. """
        return jinja2.get_jinja2(app=self.app)
    @classmethod
    def parse_set_cookie(cls, set_cookie):
        #logging.info(cls.__name__+".parse_set_cookie("+str(set_cookie)+")")
        if set_cookie:
            cookiePairList = [cookiePair.split("=") for cookiePair in set_cookie.split(";")]
            return {cookiePair[0]:cookiePair[1] for cookiePair in cookiePairList}
        return {}
    def post(self,**kwargs):
        pass
    def render_response(self, _template, **context):
        """ Renders a template and writes the result to the response. """
        rv = self.jinja2.render_template(_template, **context)
        self.response.write(rv)
    def fetch_page(self, url, option, encoding, method=None, data=None, headers=None):
        url_encoded_data = {"url":url,"option":option,"encoding":encoding}
        if data:
            url_encoded_data["data"] = data
        if headers:
            url_encoded_data["headers"] = headers
        if method:
            url_encoded_data["method"] = method
        if url:
            url_encoded_data["url"] = url
        url_encoded_data = urllib.urlencode(url_encoded_data)
        logging.info("url_encoded_data="+str(url_encoded_data))
        logging.info("https://"+self.request.host+"/fetch")
        return urlfetch.fetch(url="https://"+self.request.host+"/fetch?"+url_encoded_data,method=urlfetch.GET)
    def send_request(self, url, method=None, data=None, headers=None):
        # helper function that builds the THHP Requests, send them and return the results
        http_headers = {'Content-Type': 'application/x-www-form-urlencoded','User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36'}
        #
        #cookie_string = ""
        #for cookieName, cookieData in self.websiteCookies.iteritems():
        #    cookie_string += cookieName+"="+cookieData["value"]+";"
        #if cookie_string:
        #    headers.update({'Cookie':cookie_string})
        #
        if headers:
            http_headers.update(headers)
        #
        logging.info("pd="+str(data))
        post_data_encoded = None
        if data:
            post_data_encoded = urllib.urlencode(data)
        #
        if method:
            if "post":
                method = urlfetch.POST
            else:
                method = urlfetch.GET
        else:
            if data:
                method = urlfetch.POST
            else:
                method = urlfetch.GET
        logging.info("url="+str(url))
        logging.info("pde="+str(post_data_encoded))
        logging.info("headers="+str(http_headers))
        return urlfetch.fetch(url=url,payload=post_data_encoded,method=method,headers=http_headers)

class ListHandler(BaseHandler):
    def login(self, login_request):
        post_data = {login_request["login"]["name"]:login_request["login"]["value"],login_request["password"]["name"]:login_request["password"]["value"]}
        logging.info("login post_data="+str(post_data))
        logging.info("login fields="+str(login_request["fields"]))
        post_data.update(login_request["fields"])
        response = self.send_request(url=login_request["url"],data=login_request)
        logging.info("login headers="+str(response.headers))
        logging.info(response.content)
        if response.status_code == 200:
            if "Set-Cookie" in response.headers:
                cookie = self.parse_set_cookie(response.headers["Set-Cookie"])
                if cookie:
                    self.websiteCookies.update(cookie)
                return True
        return False
    def post(self,**kwargs):
        request_info = {}
        request_info["referer_url"] = self.request.get("referer_url")
        request_info["response_cookies"] = self.request.get("response_cookies")
        request_info["response_url"] = self.request.get("response_url")
        scraping_request = json.loads(self.request.get("json"))
        logging.info(scraping_request)
        scrap_list = []
        if "login" in scraping_request:
            logging.info("login")
            logging.info(scraping_request["login"])
        for key, value in scraping_request.iteritems():
            if key=="login":
                logging.info("login")
                request_info["login_cookies"] = self.login(value)
            elif key=="scrap_list":
                scrap_list = value
            else:
                request_info[key] = value
        for item_request in scrap_list:
            if "url" in item_request:
                item_request["urls"] = [item_request["url"]]
                del item_request["url"]
            for key, value in request_info.iteritems():
                if key not in item_request:
                    item_request[key] = value
            taskqueue.add(url='/internal/item',queue_name='scraping',params={"json":json.dumps(item_request)})

        """
            if "for_field" in item_request:
                self.scrapURLForField()
            else:
                r = self.scrapURLList()
                if r:
                    r = json.dumps(r)
                    logging.info("r="+str(r))
                    self.response.out.write(r)
        self.response.set_status(200)"""
class ItemHandler(BaseHandler):
    @classmethod
    def extract(cls, element, extractor_list):
        if extractor_list:
            scraps = {}
            for extractor in extractor_list:
                logging.info(extractor)
                if extractor["type"]=="html":
                    scraps[extractor["type"]] = etree.tostring(element, method='html', encoding="utf-8")
                elif extractor["type"]=="text":
                    scraps[extractor["type"]] = etree.tostring(element, method='text', encoding="utf-8")
                elif extractor["type"]=="trimmed-text":
                    scraps[extractor["type"]] = etree.tostring(element, method='text', encoding="utf-8").strip()
                elif extractor["type"]=="attribute":
                    if extractor["name"] in element.attrib:
                        scraps[extractor["type"]] = element.attrib[extractor["name"]]
                    else:
                        logging.warning(etree.tostring(element, method='text', encoding="utf-8")+" has no attribute '"+extractor["name"]+"' !")
                elif extractor["type"]=="method":
                    if extractor["name"]=="text":
                        scraps[extractor["type"]] = element.text
                    else:
                        logging.warning(etree.tostring(element, method='text', encoding="utf-8")+" has no method '"+extractor["name"]+"' !")
                else:
                    scraps[extractor["type"]] = etree.tostring(element, method='html', encoding="utf-8")
            return scraps
        else:
            return None
    def post(self,**kwargs):
        request = json.loads(self.request.get("json"))
        logging.info(request)
        if "for_field" in request:
            self.scrapURLForField(request)
        else:
            self.scrapURLList(request)
    @classmethod
    def selectorScrap(cls,tree,selectors,data_scraps):

        for selectorName, selectorData in selectors.iteritems():
            selector = CSSSelector(selectorData["string"])
            if not selectorName in data_scraps:
                selector_scraps = []
                data_scraps[selectorName] = selector_scraps
            else:
                selector_scraps = data_scraps[selectorName]
            for dataItem in selector(tree):
                result = cls.extract(dataItem, selectorData["extractors"])
                #logging.info(selectorData["string"]+" = "+str(result))
                if len(result)==1:
                    result = result.values()[0]
                if result:
                    if type(selector_scraps)==str:
                        selector_scraps = [selector_scraps]
                        data_scraps[selectorName] = selector_scraps
                    selector_scraps.append(result)
            if len(selector_scraps)==1:
                data_scraps[selectorName]=selector_scraps[0]
    @classmethod
    def tabularSelectorScrap(cls,tree,selectors,data_scraps):
        for tabularSelectorName, tabularSelectorData in selectors.iteritems():
            rowSelector = CSSSelector(tabularSelectorData["line_selector"])
            data_scraps[tabularSelectorName] = []
            for rowData in rowSelector(tree):
                rowScraps = []
                data_scraps[tabularSelectorName].append(rowScraps)
                for cellSelectorData in tabularSelectorData["cell_selectors"]:
                    cellSelector = CSSSelector(cellSelectorData["string"])
                    cellData = cellSelector(rowData)
                    result = ""
                    if len(cellData)==1:
                        dataItem = cellSelector(rowData)[0]
                        result = cls.extract(dataItem, cellSelectorData["extractors"])
                    else:
                        logging.info(cellSelectorData["string"]+"->"+str(cellData))
                    rowScraps.append(result)
    @classmethod
    def scrapSource(cls, source, request, encoding=None):
        data_scraps = {}
        parser = etree.HTMLParser()#encoding=encoding)
        tree = etree.fromstring(source, parser)
        if "selectors" in request:
            cls.selectorScrap(tree,request["selectors"],data_scraps)
        if "tabular_selectors" in request:
            cls.tabularSelectorScrap(tree,request["tabular_selectors"],data_scraps)
        return data_scraps
    def scrapURL(self, url, request, encoding=None):
        post_data = {}
        if "fields" in request:
            post_data.update(request["fields"])
        response = self.fetch_page(url=url,option="cache",encoding="utf_8",data=post_data)
        url_scraps = {}
        url_scraps["status"] = response.status_code
        if response.status_code == 200:
            multipart_loaded = False
            data_scraps = {}
            url_scraps["data"] = data_scraps
            url_content = [response.content]
            # parse the page
            #if not encoding:
            #    if "encoding" in request:
            #        encoding = request["encoding"]
            #    else:
            #        encoding = "utf-8"
            parser = etree.HTMLParser()#encoding=encoding)
            while (len(url_content)>0):
                tree = etree.fromstring(url_content[0], parser)
                # extract the data for all the css selectors on the page
                #logging.info("len url_content="+str(len(url_content)))
                #logging.info("multipart_loaded="+str(multipart_loaded))
                if "multipart" in request and multipart_loaded==False:
                    logging.info("multipart="+request["multipart"])
                    selector = CSSSelector(request["multipart"])
                    for page_link in selector(tree):
                        #logging.info("multipart")
                        next_url = self.extract(page_link, [{"type":"attribute","name":"href"}])
                        if next_url:
                            next_url = next_url["attribute"]
                            if not urlparse.urlparse(next_url).scheme:
                                next_url = "http://" + urlparse.urlparse(url).netloc + next_url
                        post_data = {}
                        if "fields" in request:
                            post_data.update(request["fields"])
                            #logging.info("post_data="+str(post_data))
                        part_loaded = False
                        while part_loaded==False:
                            response = self.fetch_page(url=url,option="cache",encoding="utf_8",data=post_data)
                            if response.status_code == 200:
                                url_content.append(response.content)
                                part_loaded = True
                    #logging.info("len url_content="+str(len(url_content)))
                    #logging.info("url_content="+str(url_content))
                    multipart_loaded = True
                if "selectors" in request:
                    self.selectorScrap(tree,request["selectors"],data_scraps)
                if "tabular_selectors" in request:
                    self.tabularSelectorScrap(tree,request["tabular_selectors"],data_scraps)
                del url_content[0]
                #url_content = url_content[1:]
        return url_scraps
    def scrapURLList(self,request):
        current_url = 0
        item_scraps = {"urls":{}}
        response_headers = {}
        urlList = []
        for key, value in request.iteritems():
            if key=="referer_url":
                response_headers["Referer"] = request["referer_url"]
            elif key=="response_cookies":
                response_headers["Cookie"] = request["response_cookies"]
            elif key=="selectors":
                pass
            elif key=="tabular_selectors":
                pass
            elif key=="urls":
                urlList = request["urls"]
            else:
                item_scraps[key] = value
        
        try:
            i = 0
            for url in urlList:
                logging.info(url)
                current_url += 1;
                url_string = url["string"]
                if url_string in item_scraps["urls"]:
                    urlScraps = item_scraps["urls"][url_string]
                else:
                    urlScraps = {}
                    for key, value in url.iteritems():
                        if key!="string":
                            urlScraps[key] = value
                    item_scraps["urls"][url_string] = urlScraps
                if "encoding" in url:
                    encoding = url["encoding"]
                else:
                    encoding = None
                urlScraps.update(self.scrapURL(url["string"],request,encoding=encoding))
                i += 1
                if i == 10:
                    i = 0
                    self.send_request(url=request["response_url"],data={"json":json.dumps(item_scraps)},headers=response_headers)
            response_headers["edr_eof"] = "True"
            logging.info(item_scraps)
            if "response_url" in request:
                self.send_request(url=request["response_url"],data={"json":json.dumps(item_scraps)},headers=response_headers)
            else:
                self.response.write(json.dumps(item_scraps))
        except DeadlineExceededError:
            logging.info("DeadlineExceededError")
            urls = request["urls"]
            request["urls"] = urls[current_url:]
            self.send_request(url=request["response_url"],data={"json":json.dumps(item_scraps)},headers=response_headers)
            deferred.defer(self.scrapURLList,request)

class WebsiteScraper(object):
    def scrapURLForField(self):
        scraping_item = self.scrap_list[0]
        current_url = 0
        itemScraps = {}
        urlList = scraping_item["urls"]
        fieldName = scraping_item["for_field"]["name"]
        fieldValueList = scraping_item["for_field"]["values"]
        post_data = {}
        try:
            for i, url in enumerate(urlList):
                for field in scraping_item["fields"]:
                    post_data[field["name"]] = field["value"]
                for fieldValue in fieldValueList:
                    post_data[fieldName] = fieldValue
                    response = self.send_request(url=url,data=post_data)
                    itemScraps[fieldValue] = self.scrapPage(response, scraping_item)
        except DeadlineExceededError:
            urls = self.scrap_list[0]["urls"]
            self.scrap_list[0]["urls"] = urls[current_url:]
            self.send_response()
            deferred.defer(self.scrapURLList,scraping_item)
        self.send_response()
        self.scrap_list = self.scrap_list[1:]

class SourceHandler(ailete619.beakon.handlers.UserHandler):
    def get(self,**kwargs):
        self.render_response('scrap-source.html')
    def post(self,**kwargs):
        url = self.request.get("fetchURL")
        option = self.request.get("fetchOption")
        encoding = self.request.get("fetchEncoding")
        request = {}
        selectors = self.request.get("scrapSelectors")
        if selectors:
            request["selectors"] = json.loads(selectors)
        tabular_selectors = self.request.get("scrapTabularSelectors")
        if tabular_selectors:
            request["tabular_selectors"] = json.loads(tabular_selectors)
        if option=="cache":
            cached_page = CachedPage.get_by_id(url)
            if cached_page:
                source = cached_page.source
        if not source:
            source = self.request.get("scrapSource")
            try:
                source = source.decode(encoding).encode('utf_8')
            except UnicodeDecodeError:
                pass
        if option=="force_upgrade" or (option=="cache" and not cached_page):
            cached_page = CachedPage(id=url,source=source)
            cached_page.put()
        self.context["response"] = json.dumps(ItemHandler.scrapSource(source, request))
        self.context["url"] = url
        self.context["js"] = {}
        self.context["js"]["fetchOption"] = '"'+option+'"'
        self.context["js"]["fetchEncoding"] = '"'+encoding+'"'
        self.context["source"] = source
        self.context["selectors"] = selectors
        self.context["tabular_selectors"] = tabular_selectors
        self.render_response('scrap-source.html')

class TestHandler(ailete619.beakon.handlers.UserHandler):
    def get(self,**kwargs):
        self.render_response('scrap-test.html')
    def post(self,**kwargs):
        request = {}
        url_list = self.request.get("scrapURLList")
        option = self.request.get("fetchOption")
        encoding = self.request.get("fetchEncoding")
        request["urls"] = [{"string":url,"encoding":encoding} for url in url_list.splitlines() if url]
        selectors = self.request.get("scrapSelectors")
        if selectors:
            request["selectors"] = json.loads(selectors)
        tabular_selectors = self.request.get("scrapTabularSelectors")
        if tabular_selectors:
            request["tabular_selectors"] = json.loads(tabular_selectors)
        self.context["response"] = unicode(urlfetch.fetch(url="https://"+self.request.host+"/internal/item",payload=urllib.urlencode({"json":json.dumps(request)}),method=urlfetch.POST).content,'unicode-escape')
        self.context["url_list"] = url_list
        self.context["js"] = {}
        self.context["js"]["fetchOption"] = '"'+option+'"'
        self.context["js"]["fetchEncoding"] = '"'+encoding+'"'
        self.context["selectors"] = selectors
        self.context["tabular_selectors"] = tabular_selectors
        self.render_response('scrap-test.html')

