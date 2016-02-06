
# -*- coding: utf-8 -*-
'''

@author: ailete619
'''

import datetime
from google.appengine.api import urlfetch
from google.appengine.ext import deferred
from google.appengine.runtime import DeadlineExceededError
from io import StringIO
import json
import logging
from lxml import etree
from lxml.cssselect import CSSSelector
from lxml.html import parse, fromstring
import re
import urllib
import urllib2
import webapp2
from datetime import date

class WebsiteScraper(object):
    websiteCookies = {}
    @classmethod
    def parse_set_cookie(cls, set_cookie):
        logging.info(cls.__name__+".parse_set_cookie("+str(set_cookie)+")")
        if set_cookie:
            cookiePairList = [cookiePair.split("=") for cookiePair in set_cookie.split(";")]
            return {cookiePairList[0][0]:{"value":cookiePairList[0][1]}}
        return None
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
    def __init__(self, GAE_request):
        self.response_data = []
        self.response_headers = {"Referer":GAE_request.url}
        self.scrap_list = []
        self.target_cookies = {}
        cookie = self.parse_set_cookie(GAE_request.headers["Set-Cookie"])
        if cookie:
            for c,v in cookie.iteritems():
                self.response_headers[c] = v["value"]
        self.response_url = GAE_request.headers["Referer"]
        data_request = json.loads(GAE_request.get('json'))
        if "login" in data_request:
            self.login(data_request["login"])
        self.scrap_list = data_request["scrap_list"]
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
                self.scrapURLList()
    def login(self, data):
        post_data = {data["login"]["name"]:data["login"]["value"],data["password"]["name"]:data["password"]["value"]}
        post_data.update(data["fields"])
        response = self.send_request(url=data["url"],data=post_data)
        if response.status_code == 200:
            cookie = self.parse_set_cookie(response.headers["Set-Cookie"])
            if cookie:
                self.websiteCookies.update(cookie)
            return True
        return False
    def scrapPage(self, response, item):
        pageScraps = {}
        pageScraps["status"] = response.status_code
        if response.status_code == 200:
            # parse the page
            parser = etree.HTMLParser()
            if "encoding" in item:
                encoding = item["encoding"]
            else:
                encoding = "utf-8"
            tree = etree.parse(StringIO(response.content.decode(encoding)), parser)
            # extract the data for all the css selectors on the page
            dataScraps = {}
            pageScraps["data"] = dataScraps
            if "selectors" in item:
                for selectorName, selectorData in item["selectors"].iteritems():
                    selector = CSSSelector(selectorData["string"])
                    dataScraps[selectorName] = []
                    for dataItem in selector(tree):
                        result = self.extract(dataItem, selectorData["extractors"])
                        if result:
                            dataScraps[selectorName].append(result)
            if "tabular_selectors" in item:
                for tabularSelectorName, tabularSelectorData in item["tabular_selectors"].iteritems():
                    rowSelector = CSSSelector(tabularSelectorData["line_selector"])
                    dataScraps[tabularSelectorName] = []
                    for rowData in rowSelector(tree):
                        rowScraps = []
                        dataScraps[tabularSelectorName].append(rowScraps)
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
        return pageScraps
    def scrapURL(self, url, item):
        post_data = {}
        if "fields" in item:
            post_data.update(item["fields"])
        response = self.send_request(url=url,data=post_data)
        return self.scrapPage(response, item)
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
        item_scraps = {"encoding":scraping_item["encoding"],"handler":scraping_item["handler"],"urls":[]}
        urlList = scraping_item["urls"]
        try:
            for i, url in enumerate(urlList):
                logging.info(url)
                current_url = i
                url_string = url["string"]
                if url_string in item_scraps["urls"]:
                    urlScraps = item_scraps["urls"][url_string]
                else:
                    urlScraps = {"date":url["date"]}
                    item_scraps["urls"][url_string] = urlScraps
                urlScraps.update(self.scrapURL(url,scraping_item))
        except DeadlineExceededError:
            logging.info("DeadlineExceededError")
            urls = self.scrap_list[0]["urls"]
            self.scrap_list[0]["urls"] = urls[current_url:]
            self.response_data.append(item_scraps)
            self.send_response()
            deferred.defer(self.scrapURLList,scraping_item)
        self.response_data.append(item_scraps)
        self.send_response()
        self.scrap_list = self.scrap_list[1:]
    def send_request(self, url, method=None, data=None, headers=None):
        # helper function that builds the THHP Requests, send them and return the results
        http_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
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
        logging.info(self.response_url)
        logging.info(self.response_headers)
        logging.info(self.response_data)
        self.send_request(url=self.response_url,data={"json":json.dumps(self.response_data)},headers=self.response_headers)
