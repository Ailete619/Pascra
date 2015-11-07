# -*- coding: utf-8 -*-
'''

@author: ailete619
'''

import datetime
from google.appengine.api import urlfetch
from io import StringIO
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
    def fetchAndParse(self, url, encoding="utf-8"):
        response = urlfetch.fetch(url)
        if response.status_code == 200:
            # parse the page
            parser = etree.HTMLParser()
            tree = etree.parse(StringIO(response.content.decode(encoding)), parser)
            # extract the urls on the page
            urlSel = CSSSelector('p.cnnTransSubHead')
            if len(urlSel(tree))>0:
                urls = [link.text for link in urlSel(tree)]
        return urls

class AsahiInternational(Crawler):
    name = "asahi_international"
    start_date = datetime.datetime(2012,1,1)
    @classmethod
    def generate_URL(cls,year, month,day):
        return "http://transcripts.cnn.com/TRANSCRIPTS/"+str(year)+("0"+str(month))[-2:3]+"/"+("0"+str(day))[-2:3]+"/sn.01.html"
    @classmethod
    def generate_URLs(cls):
        urls = []
        response = urlfetch.fetch("http://www.asahi.com/international/list/")
        if response.status_code == 200:
            # parse the page
            parser = etree.HTMLParser()
            tree = etree.parse(StringIO(response.content.decode(cls.encoding)), parser)
            # extract the urls on the page
            urlSel = CSSSelector('p.cnnTransSubHead')
            if len(urlSel(tree))>0:
                urls = [link.text for link in urlSel(tree)]
        return urls
    @classmethod
    def parse_page(cls, source, tree):
        # extract the title
        titleSel = CSSSelector('p.cnnTransSubHead')
        if len(titleSel(tree))>0:
            source.title = titleSel(tree)[0].text
        # extract the short text
        textSel = CSSSelector('p.cnnBodyText')
        if len(textSel(tree))>1:
            source.html = etree.tostring(textSel(tree)[2], method='html', encoding="utf-8")
            source.text = etree.tostring(textSel(tree)[2], method='text', encoding="utf-8")
    @classmethod
    def parse_page_url(cls, source, sourceURL):
        # extract the date from the URL
        dateData = re.findall(ur'(?:([0-9]{2})([0-9]{2})\/([0-9]{2})\/sn\.01\.html)', sourceURL)
        if len(dateData)>0:
            sourceDate = dateData[0]
            source.date = datetime.datetime(2000+int(sourceDate[0]),int(sourceDate[1]),int(sourceDate[2]))


class CNNStudentNewsTranscriptCrawler(Crawler):
    name = "cnn_studentnews"
    start_date = datetime.datetime(2012,1,1)
    @classmethod
    def generate_URL(cls,year, month,day):
        return "http://transcripts.cnn.com/TRANSCRIPTS/"+str(year)+("0"+str(month))[-2:3]+"/"+("0"+str(day))[-2:3]+"/sn.01.html"
    #@classmethod
    #def generate_URLs(cls):
    #    return [cls.generate_URL(15,4,30)]
    @classmethod
    def parse_page(cls, source, tree):
        # extract the title
        titleSel = CSSSelector('p.cnnTransSubHead')
        if len(titleSel(tree))>0:
            source.title = titleSel(tree)[0].text
        # extract the short text
        textSel = CSSSelector('p.cnnBodyText')
        if len(textSel(tree))>1:
            source.html = etree.tostring(textSel(tree)[2], method='html', encoding="utf-8")
            source.text = etree.tostring(textSel(tree)[2], method='text', encoding="utf-8")
    @classmethod
    def parse_page_url(cls, source, sourceURL):
        # extract the date from the URL
        dateData = re.findall(ur'(?:([0-9]{2})([0-9]{2})\/([0-9]{2})\/sn\.01\.html)', sourceURL)
        if len(dateData)>0:
            sourceDate = dateData[0]
            source.date = datetime.datetime(2000+int(sourceDate[0]),int(sourceDate[1]),int(sourceDate[2]))

class NHKKokusaihoudouArchiveCrawler(Crawler):
    encoding = "shift_jisx0213"
    language_code = "ja"
    name = "nhk_kokusaihoudou_archive"
    start_date = datetime.datetime(2014,3,31)
    @classmethod
    def generate_URL(cls,year, month,day):
        return "http://www.nhk.or.jp/kokusaihoudou/archive/"+str(year)+"/"+("0"+str(month))[-2:3]+"/"+("0"+str(month))[-2:3]+("0"+str(day))[-2:3]+".html"
    #@classmethod
    #def generate_URLs(cls):
    #    return [cls.generate_URL(15,5,1)]
    @classmethod
    def parse_page(cls, source, tree):
        # extract the date from the page (we could do it from the URL too)
        dateSel = CSSSelector('p.date')
        if len(dateSel(tree))>0:
            date_string = dateSel(tree)[0].text
            if date_string:
                dateData = re.findall(ur'(?:(?:([0-9]{4})年)(?:([0-9]{1,2})月)(?:([0-9]{1,2})日))', date_string)
                if len(dateData)>0:
                    sourceDate = dateData[0]
                    source.date = datetime.datetime(int(sourceDate[0]),int(sourceDate[1]),int(sourceDate[2]))
        # extract the title
        titleSel = CSSSelector('h3')
        if len(titleSel(tree))>0:
            source.title = titleSel(tree)[0].text
        # extract region and topic information
        otherSel = CSSSelector('nav>ul>li>a')
        if len(otherSel(tree))>1:
            regionText = otherSel(tree)[0].text
            regions = filter(lambda n: n is not None, map(lambda n: region_code[n] if n in region_code else None, re.split(u'・',regionText)))
            source.region = regions
            topicText = otherSel(tree)[1].text
            topics = re.split(u'・',topicText)
            source.topic = topics
            source.tags = regions+topics
        # extract the short text
        shortSel = CSSSelector('div.txtBlock p')
        if len(shortSel(tree))>1:
            source.short = shortSel(tree)[1].text
        # extract the lengthy transcript text
        textSel = CSSSelector('#marugotoEntry div.section01')
        if len(textSel(tree))>0:
            source.html = etree.tostring(textSel(tree)[0], method='html', encoding="utf-8")
            source.text = etree.tostring(textSel(tree)[0], method='text', encoding="utf-8")

class NHKKokusaihoudouLoungeCrawler(Crawler):
    language_code = "ja"
    name = "nhk_kokusaihoudou_lounge"
    start_date = datetime.datetime(2014,3,31)
    @classmethod
    def generate_URL(cls,year, month,day):
        return "http://www6.nhk.or.jp/kokusaihoudou/lounge/index.html?i="+str(year)+("0"+str(month))[-2:3]+("0"+str(day))[-2:3]
    #@classmethod
    #def generate_URLs(cls):
    #    return [cls.generate_URL(15,5,1)]
    @classmethod
    def parse_page(cls, source, tree):
        # extract the title
        titleSel = CSSSelector('div.txtBlock h3')
        if len(titleSel(tree))>0:
            source.title = titleSel(tree)[0].text
        # extract the short text
        shortSel = CSSSelector('div.txtBlock p')
        if len(shortSel(tree))>1:
            source.html = etree.tostring(shortSel(tree)[1], method='html', encoding="utf-8")
            source.short = shortSel(tree)[1].text
    @classmethod
    def parse_page_url(cls, source, sourceURL):
        # extract the date from the URL
        dateData = re.findall(ur'(?:=([0-9]{2})([0-9]{2})([0-9]{2}))', sourceURL)
        if len(dateData)>0:
            sourceDate = dateData[0]
            source.date = datetime.datetime(2000+int(sourceDate[0]),int(sourceDate[1]),int(sourceDate[2]))
