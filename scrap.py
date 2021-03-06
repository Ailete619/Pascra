# -*- coding: utf-8 -*-

from ailete619.beakon import cookiejar, handlers, log
from fetch import CachedPage
from google.appengine.api import taskqueue, urlfetch
from google.appengine.ext import deferred, ndb
from google.appengine.runtime import DeadlineExceededError
import json
import logging
from lxml import etree
from lxml.cssselect import CSSSelector
import secrets
import urlparse

class ScrapString(ndb.Model):
    source = ndb.TextProperty()

class ScrapingHandler(handlers.WithoutSessionHandler):
    def post(self):
        parameters = {}
        log.info(self.request.get("json"))
        parameters['referer_url'] = self.request.url
        if "Set-Cookie" in self.request.headers:
            parameters['response_cookies'] = self.request.headers["Set-Cookie"]
        parameters['response_url'] = self.request.headers.get("Referer")
        parameters['json'] = self.request.get("json")
        logging.info(json.dumps(parameters))
        taskqueue.add(url='/internal/list',queue_name='scraping',params=parameters)
        self.response.set_status(200)
        
class ScrapingInternalHandler(handlers.TaskHandler):
    queue_name = "scraping"
    def fetch_page(self, url, option, encoding, data=None, headers=None):
        log.info(self.__class__.__name__+".fetch_page(url='"+str(url)+"',option='"+str(option)+"',encoding='"+str(encoding)+"')")
        fetch_data = {"url":url,"option":option,"encoding":encoding}
        if headers:
            fetch_data["headers"] = headers
        if data:
            fetch_data["data"] = data
        fetch_url = "https://"+self.request.host+"/fetch"
        return self.send_request(url=fetch_url,method=urlfetch.GET,data=fetch_data)

class ListHandler(ScrapingInternalHandler):
    def login(self, login_request):
        post_data = {login_request["login"]["name"]:login_request["login"]["value"],login_request["password"]["name"]:login_request["password"]["value"]}
        log.info("login post_data="+str(post_data))
        log.info("login fields="+str(login_request["fields"]))
        post_data.update(login_request["fields"])
        response = self.send_request(url=login_request["url"],data=login_request)
        log.info("login headers="+str(response.headers))
        log.info(response.content)
        if response.status_code == 200:
            if "Set-Cookie" in response.headers:
                cookie = cookiejar.get_cookies(response.headers)
                if cookie:
                    self.websiteCookies.update(cookie)
                return True
        return False
    def post(self,**kwargs):
        log.info("list handler POST")
        log.info("kwrags="+str(kwargs))
        request_info = {}
        request_info["referer_url"] = self.request.get("referer_url")
        request_info["response_url"] = self.request.get("response_url")
        scraping_request = json.loads(self.request.get("json"))
        log.info(scraping_request)
        scrap_list = []
        if "login" in scraping_request:
            log.info("login")
            log.info(scraping_request["login"])
        for key, value in scraping_request.iteritems():
            if key=="login":
                log.info("login")
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
                    log.info("r="+str(r))
                    self.response.out.write(r)
        self.response.set_status(200)"""
class ItemHandler(ScrapingInternalHandler):
    @classmethod
    def extract(cls, element, extractor_list):
        if extractor_list:
            scraps = {}
            for extractor in extractor_list:
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
                        log.warning(etree.tostring(element, method='text', encoding="utf-8")+" has no attribute '"+extractor["name"]+"' !")
                elif extractor["type"]=="method":
                    if extractor["name"]=="text":
                        scraps[extractor["type"]] = element.text
                    else:
                        log.warning(etree.tostring(element, method='text', encoding="utf-8")+" has no method '"+extractor["name"]+"' !")
                else:
                    scraps[extractor["type"]] = etree.tostring(element, method='html', encoding="utf-8")
            return scraps
        else:
            return None
    def post(self):
        request = json.loads(self.request.get("json"))
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
                        log.info(cellSelectorData["string"]+"->"+str(cellData))
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
    def scrapURL(self, url, request, option="cache", encoding="utf_8"):
        post_data = {}
        if "fields" in request:
            post_data.update(request["fields"])
        response = self.fetch_page(url=url,option=option,encoding=encoding,data=post_data)
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
                if "multipart" in request and multipart_loaded==False:
                    selector = CSSSelector(request["multipart"])
                    for page_link in selector(tree):
                        next_url = self.extract(page_link, [{"type":"attribute","name":"href"}])
                        if next_url:
                            next_url = next_url["attribute"]
                            if not urlparse.urlparse(next_url).scheme:
                                next_url = "http://" + urlparse.urlparse(url).netloc + next_url
                        post_data = {}
                        if "fields" in request:
                            post_data.update(request["fields"])
                        part_loaded = False
                        while part_loaded==False:
                            response = self.fetch_page(url=url,option="cache",encoding="utf_8",data=post_data)
                            if response.status_code == 200:
                                url_content.append(response.content)
                                part_loaded = True
                    multipart_loaded = True
                if "selectors" in request:
                    self.selectorScrap(tree,request["selectors"],data_scraps)
                if "tabular_selectors" in request:
                    self.tabularSelectorScrap(tree,request["tabular_selectors"],data_scraps)
                del url_content[0]
        return url_scraps
    def scrapURLList(self,request):
        logging.info(request)
        current_url = 0
        item_scraps = {"urls":{}}
        response_headers = {}
        urlList = []
        for key, value in request.iteritems():
            if key=="referer_url":
                response_headers["Referer"] = request["referer_url"]
            elif key=="selectors":
                pass
            elif key=="tabular_selectors":
                pass
            elif key=="urls":
                urlList = request["urls"]
            else:
                item_scraps[key] = value
        if urlList:
            try:
                i = 0
                for url in urlList:
                    log.info("url="+str(url))
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
                    elif "encoding" in request:
                        encoding = request["encoding"]
                    else:
                        encoding = "utf_8"
                    if "option" in url:
                        option = url["option"]
                    elif "option" in request:
                        option = request["option"]
                    else:
                        option = "cache"
                    urlScraps.update(self.scrapURL(url=url["string"],request=request,encoding=encoding,option=option))
                    i += 1
                    logging.info(request["response_url"])
                    if "response_url" in request and request["response_url"]:
                        if i == 10:
                            i = 0
                            response = self.send_request(url=request["response_url"],method=urlfetch.POST,data={"login":secrets.login_sources,"password":secrets.password_sources,"json":json.dumps(item_scraps)},headers=response_headers)
                            logging.info(response.status_code)
                            item_scraps["urls"] = {}
                logging.info(request["response_url"])
                if "response_url" in request and request["response_url"]:
                    response = self.send_request(url=request["response_url"],method=urlfetch.POST,data={"login":secrets.login_sources,"password":secrets.password_sources,"json":json.dumps(item_scraps)},headers=response_headers)
                    logging.info(response.status_code)
                    logging.info(response.content)
                else:
                    self.response.write(json.dumps(item_scraps))
            except DeadlineExceededError:
                log.info("DeadlineExceededError")
                urls = request["urls"]
                request["urls"] = urls[current_url:]
                self.send_request(url=request["response_url"],method=urlfetch.POST,data={"login":secrets.login_sources,"password":secrets.password_sources,"json":json.dumps(item_scraps)},headers=response_headers)
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

class HelpHandler(handlers.UserHandler):
    def get(self,**kwargs):
        self.render_response('scrap-help.html')

class SourceHandler(handlers.UserHandler):
    def get(self,**kwargs):
        self.render_response('scrap-source.html')
    def post(self,**kwargs):
        url = self.request.get("scrapURL")
        log.info(url)
        option = self.request.get("cacheOption")
        log.info(option)
        encoding = self.request.get("sourceEncoding")
        log.info(encoding)
        request = {}
        selectors = self.request.get("scrapSelectors")
        log.info(selectors)
        if selectors:
            request["selectors"] = json.loads(selectors)
        tabular_selectors = self.request.get("scrapTabularSelectors")
        log.info(tabular_selectors)
        if tabular_selectors:
            request["tabular_selectors"] = json.loads(tabular_selectors)
        source = None
        if option=="cache":
            cached_page = CachedPage.get_by_id(url)
            if cached_page:
                source = cached_page.source
        if not source:
            source = self.request.get("scrapSource")
            log.info(source)
            so = ScrapString(source=source)
            so.put()
            
            try:
                source = so.source.decode(encoding,'ignore')#.encode('utf_8')
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

class TestHandler(handlers.AdminHandler):
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
        self.context["response"] = unicode(self.send_request(url="https://"+self.request.host+"/internal/item",data={"json":json.dumps(request)},method=urlfetch.POST).content,'unicode-escape')
        self.context["url_list"] = url_list
        self.context["js"] = {}
        self.context["js"]["fetchOption"] = '"'+option+'"'
        self.context["js"]["fetchEncoding"] = '"'+encoding+'"'
        self.context["selectors"] = selectors
        self.context["tabular_selectors"] = tabular_selectors
        self.render_response('scrap-test.html')

