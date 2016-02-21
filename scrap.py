
# -*- coding: utf-8 -*-
'''

@author: ailete619
'''

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

import logging
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
        return urlfetch.fetch(url=url,payload=post_data_encoded,method=method,headers=http_headers)

class ListHandler(BaseHandler):
    def login(self, login_request):
        post_data = {login_request["login"]["name"]:login_request["login"]["value"],login_request["password"]["name"]:login_request["password"]["value"]}
        post_data.update(login_request["fields"])
        response = self.send_request(url=login_request["url"],login_request=post_data)
        if response.status_code == 200:
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
        scrap_list = []
        for key, value in scraping_request.iteritems():
            if key=="login":
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
                    self.GAE_response.out.write(r)
        self.GAE_response.set_status(200)"""
class ItemHandler(BaseHandler):
    def extract(self, element, extractor_list):
        if extractor_list:
            scraps = {}
            for extractor in extractor_list:
                if extractor["type"]=="html":
                    scraps[extractor["type"]] = etree.tostring(element, method='html', encoding="utf-8")
                elif extractor["type"]=="text":
                    scraps[extractor["type"]] = etree.tostring(element, method='text', encoding="utf-8")
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
    def scrapURL(self, url, request, encoding=None):
        post_data = {}
        if "fields" in request:
            post_data.update(request["fields"])
        response = self.send_request(url=url,data=post_data)
        url_scraps = {}
        url_scraps["status"] = response.status_code
        if response.status_code == 200:
            multipart_loaded = False
            data_scraps = {}
            url_scraps["data"] = data_scraps
            content = [response.content]
            # parse the page
            #if not encoding:
            #    if "encoding" in request:
            #        encoding = request["encoding"]
            #    else:
            #        encoding = "utf-8"
            parser = etree.HTMLParser()#encoding=encoding)
            while len(content)>=0:
                tree = etree.fromstring(content[0], parser)
                # extract the data for all the css selectors on the page
                if "multipart" in request and multipart_loaded==False:
                    selector = CSSSelector(request["multipart"])
                    for page_link in selector(tree):
                        url = self.extract(page_link, {"type":"attribute","name":"href"})
                        if "fields" in request:
                            post_data.update(request["fields"])
                        part_loaded = False
                        while part_loaded==False:
                            response = self.send_request(url=url,data=post_data)
                            if response.status_code == 200:
                                content.append(response.content)
                                part_loaded = True
                    multipart_loaded = True
                if "selectors" in request:
                    for selectorName, selectorData in request["selectors"].iteritems():
                        selector = CSSSelector(selectorData["string"])
                        selector_scraps = []
                        data_scraps[selectorName] = selector_scraps
                        for dataItem in selector(tree):
                            result = self.extract(dataItem, selectorData["extractors"])
                            #logging.info(selectorData["string"]+" = "+str(result))
                            if len(result)==1:
                                result = result.values()[0]
                            if result:
                                selector_scraps.append(result)
                        if len(selector_scraps)==1:
                            data_scraps[selectorName]=selector_scraps[0]
                if "tabular_selectors" in request:
                    for tabularSelectorName, tabularSelectorData in request["tabular_selectors"].iteritems():
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
                                    result = self.extract(dataItem, cellSelectorData["extractors"])
                                else:
                                    logging.info(cellSelectorData["string"]+"->"+str(cellData))
                                rowScraps.append(result)
                content = content[1:]
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
            self.send_request(url=request["response_url"],data={"json":json.dumps(item_scraps)},headers=response_headers)
        except DeadlineExceededError:
            logging.info("DeadlineExceededError")
            urls = request["urls"]
            request["urls"] = urls[current_url:]
            self.send_request(url=request["response_url"],data={"json":json.dumps(item_scraps)},headers=response_headers)
            deferred.defer(self.scrapURLList,request)

class WebsiteScraper(object):
    websiteCookies = {}

    @classmethod
    def parse_set_cookie(cls, set_cookie):
        #logging.info(cls.__name__+".parse_set_cookie("+str(set_cookie)+")")
        if set_cookie:
            cookiePairList = [cookiePair.split("=") for cookiePair in set_cookie.split(";")]
            return {cookiePairList[0][0]:{"value":cookiePairList[0][1]}}
        return None

    def __init__(self, GAE_request, GAE_response):
        logging.info("headers="+str(GAE_request.headers))
        self.response_data = []
        self.response = {"data":self.response_data}
        self.response_headers = {"Referer":GAE_request.url}
        self.scrap_list = []
        self.target_cookies = {}
        cookie = self.parse_set_cookie(GAE_request.headers["Set-Cookie"])
        if cookie:
            for c,v in cookie.iteritems():
                self.response_headers[c] = v["value"]
        self.GAE_response = GAE_response
        if "Referer" in GAE_request.headers:
            self.response_url = GAE_request.headers["Referer"]
        else:
            self.response_url = None
        data_request = json.loads(GAE_request.get('json'))

        for key, value in data_request.iteritems():
            if key=="login":
                self.login(value)
            elif key=="scrap_list":
                self.scrap_list = value
            else:
                self.response[key] = value
        for item in self.scrap_list:
            if "url" in item:
                item["urls"] = [item["url"]]
                del item["url"]
            if not "urls" in item:
                logging.warning("Error: no urls to scrap in this item!")
                continue
            if "for_field" in item:
                self.scrapURLForField()
            else:
                r = self.scrapURLList()
                if r:
                    r = json.dumps(r)
                    logging.info("r="+str(r))
                    self.GAE_response.out.write(r)
        self.GAE_response.set_status(200)

    def scrapPage(self, response, item, encoding=None):
        def make_unicode(input):
            if type(input) != unicode:
                input =  input.decode('utf-8','ignore')
                return input
            else:
                return input
        page_scraps = {}
        page_scraps["status"] = response.status_code
        if response.status_code == 200:
            textu = "#"
            exception_list = []
            encoding_list = [
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
                                "iso8859_11",
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
                                "utf_8_sig"
                                ]
            for encoding in encoding_list:
                good = True
                try:
                    parser = etree.HTMLParser()
                        
                    tree = etree.fromstring(GAE_response.content.decode(encoding), parser)
                    #textu = GAE_response.content.decode(encoding)
                except Exception as e:
                    exception_list.append(encoding)
                    good = False
                #if good:
                    #logging.info(encoding)
            #logging.info(exception_list)
            #logging.info(textu)
            # parse the page
            if not encoding:
                if "encoding" in item:
                    encoding = item["encoding"]
                else:
                    encoding = "utf-8"
            parser = etree.HTMLParser()#encoding=encoding)
            #tree = etree.parse(make_unicode(GAE_response.content), parser)
            #tree = etree.parse(StringIO(GAE_response.content.decode('utf-8-sig')), parser)
            tree = etree.fromstring(response.content, parser)
            # extract the data for all the css selectors on the page
            data_scraps = {}
            page_scraps["data"] = data_scraps
            if "selectors" in item:
                for selectorName, selectorData in item["selectors"].iteritems():
                    selector = CSSSelector(selectorData["string"])
                    selector_scraps = []
                    data_scraps[selectorName] = selector_scraps
                    for dataItem in selector(tree):
                        result = self.extract(dataItem, selectorData["extractors"])
                        #logging.info(selectorData["string"]+" = "+str(result))
                        if len(result)==1:
                            result = result.values()[0]
                        if result:
                            selector_scraps.append(result)
                    if len(selector_scraps)==1:
                        data_scraps[selectorName]=selector_scraps[0]
            if "tabular_selectors" in item:
                for tabularSelectorName, tabularSelectorData in item["tabular_selectors"].iteritems():
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
                                result = self.extract(dataItem, cellSelectorData["extractors"])
                            else:
                                logging.info(cellSelectorData["string"]+"->"+str(cellData))
                            rowScraps.append(result)
        return page_scraps
    def scrapURL(self, url, item, encoding=None):
        post_data = {}
        if "fields" in item:
            post_data.update(item["fields"])
        #logging.info(url)
        response = self.send_request(url=url,data=post_data)
        #logging.info(GAE_response.content)
        return self.scrapPage(response, item, encoding)
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
    def scrapURLList(self):
        scraping_item = self.scrap_list[0]
        current_url = 0
        item_scraps = {"encoding":scraping_item["encoding"],"handler":scraping_item["handler"],"urls":{}}
        urlList = scraping_item["urls"]
        try:
            for i, url in enumerate(urlList):
                #logging.info(url)
                current_url = i
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
                urlScraps.update(self.scrapURL(url["string"],scraping_item,encoding=encoding))
            self.response_headers["edr_eof"] = "True"
        except DeadlineExceededError:
            logging.info("DeadlineExceededError")
            urls = self.scrap_list[0]["urls"]
            self.scrap_list[0]["urls"] = urls[current_url:]
            self.response_data.append(item_scraps)
            self.send_response()
            deferred.defer(self.scrapURLList,scraping_item)
        self.response_data.append(item_scraps)
        if self.response_url:
            self.send_response()
        else:
            return self.response_data
        #self.scrap_list = self.scrap_list[1:]
    def send_request(self, url, method=None, data=None, headers=None):
        # helper function that builds the THHP Requests, send them and return the results
        http_headers = {'Content-Type': 'application/x-www-form-urlencoded','User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36'}
        #
        cookie_string = ""
        for cookieName, cookieData in self.websiteCookies.iteritems():
            cookie_string += cookieName+"="+cookieData["value"]+";"
        if cookie_string:
            headers.update({'Cookie':cookie_string})
        #
        if headers:
            http_headers.update(headers)
        #
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
        return urlfetch.fetch(url=url,payload=post_data_encoded,method=method,headers=http_headers)
    def send_response(self):
        self.send_request(url=self.response_url,data={"json":json.dumps(self.response)},headers=self.response_headers)
