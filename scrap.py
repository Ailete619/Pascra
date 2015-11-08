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
