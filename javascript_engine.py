
# -*- coding: utf-8 -*-
'''

@author: ailete619
'''
from collections import deque
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import logging
import urllib
import urllib2
import urlparse
import webapp2

class CachedPage(ndb.Model):
    source = ndb.TextProperty()
    headers = ndb.TextProperty()

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

class FSMBuilder(object):
    index = 0
    input = ""
    current_nodes = []
    first_node_list = deque(maxlen=2)
    last_node_list = deque(maxlen=2)
    stack = deque()
    fsm = {}
    def add(self, character, new_node):
        for node in self.last_node_list[-1]:
            if character in node:
                raise Exception
            else:
                node[character] = new_node
        self.last_node_list.append([new_node])
    def append(self, character, new_node):
        for node in self.stack[-1]:
            if character in node:
                raise Exception
            else:
                node[character] = new_node
        self.stack.pop()
        self.stack.append([new_node])
    def handle_backslash(self):
        escaped_characters = {"\'":"\'","\"":"\"","\\":"\\","n":"\n","r":"\r","t":"\t","b":"\b"}
        self.index+=1
        character = self.input[self.index]
        if character in escaped_characters:
            new_node = {}
            self.append(escaped_characters[character], new_node)
    def handle_closing_parenthesis(self):
        last = self.stack.pop()
        self.stack[-1].append(last[0])
        self.stack.rotate(1)
        self.previous_node = self.stack.pop()
        self.stack.rotate(-1)
    def handle_opening_parenthesis(self):
        self.stack.append([])
        self.stack.append(self.stack[-2])
    def handle_pipe(self):
        last = self.stack.pop()
        self.stack[-1].extend(last)
        self.stack.extend([self.stack[-2]])
    def handle_plus(self): # ***
        last = self.stack[-2]
        for node in self.stack[-1]:
            for key, value in last.itertools():
                node[key] = value
    def handle_question_mark(self):
        logging.info("stack="+str(self.stack))
        last = self.stack.pop()
        self.stack[-1].extend(last)
        logging.info("stack="+str(self.stack))
    def handle_star(self, current_node, input):
        current_node[input] = current_node
        return current_node
        new_node = {}
        current_node[input] = new_node
        new_node[input] = new_node
        return new_node
    def set_current_nodes(self, new_nodes):
        self.current_nodes = new_nodes
    def parse(self):
        self.input = "a(bb|cc)?d"
        self.stack.append([self.fsm])
        self.stack.append([self.fsm])
        logging.info("fsm="+str(self.fsm))
        logging.info("stack="+str(self.stack))
        #last_index = len(self.input)-1
        while self.index<len(self.input):
            character = self.input[self.index]
            logging.info("char="+character)
            if character=="\\":
                self.handle_backslash()
            elif character=="|":
                self.handle_pipe()
            elif character=="+":
                self.handle_plus()
            elif character=="?":
                self.handle_question_mark()
            elif character=="*":
                self.handle_star()
            elif character=="(":
                self.handle_opening_parenthesis()
            elif character==")":
                self.handle_closing_parenthesis()
            else:
                new_node = {}
                self.previous_character = character
                self.append(character, new_node)
                #self.set_current_nodes([new_node])
            #if self.index==last_index:
            #    node["type"] = regex_type
            self.previous_node = self.stack[-1][0]
            logging.info("fsm="+str(self.fsm))
            logging.info("stack="+str(self.stack))
            self.index += 1
            #last_character = character

def is_identifier_start(character):
    if character in u"_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
        return True
    return False

def is_whitespace(character):
    if character in u"_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
        return True
    return False
    

class TestHandler(webapp2.RequestHandler):
    def scan(self):
        test_string = "function"
        
        
    def get(self,**kwargs):
        js_string = """
        // •\Ž¦ƒy[ƒWƒ^ƒCƒvF0:pc  1:sp  2:pctop from sp
var disp_page_ = 0;

// UAƒ^ƒCƒvF0:pc  1:sp
var ua_ = 0;

// ƒNƒbƒL[—pÝ’è
var cookie_name_ = "nol_kokusaihoudou";
var cookie_time_ = 90;

//for kokusaihoudou
var cookie_domain_ = "nhk.or.jp";
var cookie_path_ = "/kokusaihoudou";

// ƒ[ƒhŽžˆ—
(function(){
    // UA”»•Ê
    function checkUaMethod(){
        var params = nol_getDeviceType();
        if(params[0] == "smart") ua_ = 1;
        // ƒNƒbƒL[Žæ“¾F0:pc  1:sp
        if (ua_ == 1 && GetCookie(cookie_name_) == 0) {
            //alert('ƒXƒ}ƒz‚ÅPC');
            disp_page_ = 2;
        } else if (ua_ == 1) {
            //alert('ƒXƒ}ƒz‚ÅƒXƒ}ƒz');
            disp_page_ = 1;
        } else {
            //alert('PC‚ÅPC');
            disp_page_ = 0;
        }
        //alert(disp_page_);
    }
    checkUaMethod();
})();

//--------ƒNƒbƒL[—pŠÖ”--------//
// ƒNƒbƒL[ƒZƒbƒg
function SetCookie(key, val){
    var period = cookie_time_;
    var nowtime = new Date().getTime();
    var clear_time = new Date(nowtime + (60 * 60 * 24 * 1000 * period));
    var expires = clear_time.toGMTString();

    document.cookie = key + "=" + escape(val) + ";domain=" + cookie_domain_ + ";path="+cookie_path_ + ";expires="+expires;
}

// ƒNƒbƒL[Žæ“¾
function GetCookie(key){
    var i, x, y, ARRcookies = document.cookie.split(';');
    for (var i = 0; i<ARRcookies.length; i++) {
        x = ARRcookies[i].substr(0,ARRcookies[i].indexOf('='));
        y = ARRcookies[i].substr(ARRcookies[i].indexOf('=')+1);
        x = x.replace(/^\s+|\s+$/g,'');
        if (x == key){
            //alert(y);
            return unescape(y);
        }
    }
}

//--------ƒy[ƒWØ‘Ö—pŠÖ”--------//
// ƒy[ƒWØ‘Ö
function hrefChange(mode){
    //alert(mode);
    SetCookie(cookie_name_, mode);
    window.location.reload();
}

// PCƒy[ƒW‚ÖØ‘Ö
function pcClickHandler(){
    hrefChange(0);
}

// ƒXƒ}[ƒgƒtƒHƒ“ƒy[ƒW‚ÖØ‘Ö
function spClickHandler(){
    hrefChange(1);
}"""
        T = FSMBuilder()
        T.parse()
        logging.info(T.fsm)            
                
        self.response.write(T.fsm)
        
