
# -*- coding: utf-8 -*-
'''

@author: ailete619
'''

import datetime
from google.appengine.api import urlfetch
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


class BulkScraper(object):
    pass

class PageScraper(object):
    @classmethod
    def fetch(cls, jsonData):
        logging.info('fetch')
        data = json.loads(jsonData)
        logging.info(data)
        scraps = {}
        response = urlfetch.fetch(data["url"])
        scraps["status"] = response.status_code
        if response.status_code == 200:
            scraps["data"] = {}
            # parse the page
            parser = etree.HTMLParser()
            encoding = data["encoding"] or "utf-8"
            tree = etree.parse(StringIO(response.content.decode(encoding)), parser)
            # extract the data for all the css selectors on the page
            for selector in data["selectors"]:
                selectorData = CSSSelector(selector)
                scraps["data"][selector] = []
                for dataItem in selectorData(tree):
                    scraps["data"][selector].append(etree.tostring(dataItem, method='html', encoding="utf-8"))
        return scraps
class WebsiteScraper(object):
    websiteCookies = {}
    def login(self, data):
        http_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        post_data = {data["login"]["name"]:data["login"]["value"],data["password"]["name"]:data["password"]["value"]}
        for field in data["fields"]:
            post_data[field["name"]] = field["value"]
        post_data_encoded = urllib.urlencode(post_data)
        response = urlfetch.fetch(url=data["url"],payload=post_data_encoded,method=urlfetch.POST,headers=http_headers)
        if response.status_code == 200:
            cookie = response.headers.get('set-cookie')
            cookiePairList = [cookiePair.split("=") for cookiePair in cookie.split(";")]
            self.websiteCookies[cookiePairList[0][0]] = {"value":cookiePairList[0][1]}
            return True
        return False
    def sendRequest(self, url, method=None, data=None, headers=None):
        cookieString = ""
        for cookieName, cookieData in self.websiteCookies.iteritems():
            cookieString += cookieName+"="+cookieData["value"]+";"
        http_headers = {'Content-Type': 'application/x-www-form-urlencoded','Cookie':cookieString}
        if headers is not None:
            http_headers.update(headers)
        post_data_encoded = urllib.urlencode(data)
        if method == None:
            if data == None:
                method = urlfetch.GET
            else:
                method = urlfetch.POST
        return urlfetch.fetch(url=url,payload=post_data_encoded,method=method,headers=http_headers)
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
                        if "extractor" in selectorData:
                            extractor = selectorData["extractor"]
                            if extractor["type"]=="attribute":
                                if extractor["name"] in dataItem.attrib:
                                    result = dataItem.attrib[extractor["name"]]
                                else:
                                    logging.warning(etree.tostring(dataItem, method='text', encoding="utf-8")+"has no attribute : "+extractor["name"])
                            elif extractor["type"]=="text":
                                result = etree.tostring(dataItem, method='text', encoding="utf-8")
                            elif extractor["type"]=="method":
                                if extractor["name"]=="text":
                                    result = dataItem.text
                                else:
                                    logging.warning(etree.tostring(dataItem, method='text', encoding="utf-8")+"has no method : "+extractor["name"])
                            else:
                                result = etree.tostring(dataItem, method='html', encoding="utf-8")
                        else:
                            result = etree.tostring(dataItem, method='html', encoding="utf-8")
                        if result is not None:
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
                                if "extractor" in cellSelectorData:
                                    extractor = cellSelectorData["extractor"]
                                    if extractor["type"]=="attribute":
                                        if extractor["name"] in dataItem.attrib:
                                            result = dataItem.attrib[extractor["name"]]
                                        else:
                                            logging.warning(etree.tostring(dataItem, method='text', encoding="utf-8")+"has no attribute : "+extractor["name"])
                                    elif extractor["type"]=="text":
                                        result = etree.tostring(dataItem, method='text', encoding="utf-8")
                                    elif extractor["type"]=="method":
                                        if extractor["name"]=="text":
                                            result = dataItem.text
                                        else:
                                            logging.warning(etree.tostring(dataItem, method='text', encoding="utf-8")+"has no method : "+extractor["name"])
                                    else:
                                        result = etree.tostring(dataItem, method='html', encoding="utf-8")
                                else:
                                    result = etree.tostring(dataItem, method='html', encoding="utf-8")
                            else:
                                logging.info(cellSelectorData["string"]+"->"+str(cellData))
                            rowScraps.append(result)
        return pageScraps
    def scrapURL(self, url, item):
        post_data = {}
        for field in item["fields"]:
            post_data[field["name"]] = field["value"]
        response = self.sendRequest(url=url,data=post_data)
        return self.scrapPage(response, item)
    def scrapURLForField(self, item):
        itemScraps = {}
        if "urls" in item:
            url = item["urls"][0]
            logging.warning("Error: more than one url in inscrapURLForField()")
        elif "url" in item:
            url = [item["url"]]
        else:
            logging.warning("Error: no url inscrapURLForField()")
        fieldName = item["for_field"]["name"]
        fieldValueList = item["for_field"]["values"]
        post_data = {}
        for field in item["fields"]:
            post_data[field["name"]] = field["value"]
        for fieldValue in fieldValueList:
            post_data[fieldName] = fieldValue
            response = self.sendRequest(url=url,data=post_data)
            itemScraps[fieldValue] = self.scrapPage(response, item)
        return itemScraps
    def scrapURLList(self, item):
        itemScraps = {}
        if "urls" in item:
            urlList = item["urls"]
        elif "url" in item:
            urlList = [item["url"]]
        else:
            logging.warning("Error: no url inscrapURLList()")
        for url in urlList:
            if url in itemScraps:
                urlScraps = itemScraps[url]
            else:
                urlScraps = {}
                itemScraps[url] = urlScraps
            urlScraps.update(self.scrapURL(url,item))
        return itemScraps
    def scrap(self, data):
        # tabular data output
        scraps = []
        if "login" in data:
            self.login(data["login"])
        scrapList = data["scrap_list"]
        for item in scrapList:
            if "for_field" in item:
                scraps.append(self.scrapURLForField(item))
            else:
                scraps.append(self.scrapURLList(item))
        return scraps
