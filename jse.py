
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
from ailete619.beakon.handlers import AdminHandler

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

def parse_number(string,index):
    pass

def parse_string(string,index):
    quote = string[index]
    start = index
    index = index+1
    while index<len(string) and string[index]!=quote:
        index += 1
    return {"index":(index+1),"position":start,"string":string[start:(index+1)],"type":"string","value":string[(start+1):index]}

def is_end_of_line(string,index):
    if string[index]=="\n":
        return 1
    elif string[index]=="\r":
        if string[index+1]=="\n":
            return 2
        return 1
    return 0

def parse_single_line_comment(string,index):
    offset = is_end_of_line(string,index)
    while index<len(string) and offset==0:
        index += 1
        offset = is_end_of_line(string,index)
    return {"index":index+offset}
    
def parse_multiline_comment(string,index):
    while index<len(string):
        index +=1
        if string[index]=="*":
            index +=1
            if string[index]=="/":
                break
    return {"index":(index+1)}

def parse_operator(string,index):
    """fsm = {}
    for operator in ["+","-","*","/","%","++","--","=","+=","-=","*=","/=","%=","==","===","!=","!==","<","<=",">",">=","&&","||","!","&","|","^","~","<<",">>",">>>"]:
        node = fsm
        for character in operator:
            if character not in node:
                node[character] = {}
            node = node[character]
        node["terminal"] = {"handler":parse_operator}
    logging.info("operator fsm="+str(fsm))
    """
    fsm = {
           '!':{'terminal':{'handler':parse_operator}},
                '=':{'terminal':{'handler':parse_operator},
                     '=':{'terminal':{'handler':parse_operator}}}},
           '%':{'terminal':{'handler':parse_operator},
                '=':{'terminal':{'handler':parse_operator}}},
           '&':{'terminal':{'handler':parse_operator},
                '&':{'terminal':{'handler':parse_operator}}},
           '+':{'terminal':{'handler':parse_operator},
                '+':{'terminal':{'handler':parse_operator}},
                '=':{'terminal':{'handler':parse_operator}}},
           '*':{'terminal':{'handler':parse_operator},
              '=':{'terminal':{'handler':parse_operator}}},
           '-':{'terminal':{'handler':parse_operator},
                '=':{'terminal':{'handler':parse_operator}},
                '-':{'terminal':{'handler':parse_operator}}},
           '/':{'terminal':{'handler':parse_operator},
                '=':{'terminal':{'handler':parse_operator}}},
           '|':{'terminal':{'handler':parse_operator},
                '|':{'terminal':{'handler':parse_operator}}},
           '~':{'terminal':{'handler':parse_operator}},
           '^':{'terminal':{'handler':parse_operator}},
           '=':{'terminal':{'handler':parse_operator},
                '=':{'terminal':{'handler':parse_operator},
                     '=':{'terminal':{'handler':parse_operator}}}},
           '<':{'terminal':{'handler':parse_operator},
                '=':{'terminal':{'handler':parse_operator}},
                '<':{'terminal':{'handler':parse_operator}}},
            '>':{'terminal':{'handler':parse_operator},
                 '=':{'terminal':{'handler':parse_operator}},
                 '>':{'terminal':{'handler':parse_operator},
                      '>':{'terminal':{'handler':parse_operator}}}}}
    start = index
    node = fsm
    character = string[index]
    logging.info("    character='"+str(character)+"'")
    while index<len(string) and character in node:
        node = node[character]
        index += 1
        character = string[index]
        logging.info("    character='"+str(character)+"'")
    if "terminal" in node:
        return {"index":index,"start":start,"string":string[start:index],"type":"operator"}
    else:
        return {"index":index,"start":start,"type":"error"}

def parse_separator(string,index):
    start = index
    index += 1
    return {"index":index,"start":start,"string":string[start:index],"type":"separator"}

def scan(string,index):
    length = len(string)
    fsm = {}
    for char_range in [
                       {"list":"_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ","handler":parse_identifier},
                       {"list":"\'\"","handler":parse_string},
                       {"list":"0123456789","handler":parse_number},
                       {"list":" \n\r\t","handler":eat_whitespace},
                       {"list":"!%&=-^|@+*<>?/\\","handler":parse_operator},
                       {"list":",.:;()[]{}","handler":parse_separator}
                       ]:
        node = fsm
        for character in char_range["list"]:
            if character not in node:
                node[character] = {}
                node[character]["terminal"] = {"handler":char_range["handler"]}
    for combination in [
                        {"string":"//","handler":parse_single_line_comment},
                        {"string":"/*","handler":parse_multiline_comment},
                        ]:
        node = fsm
        for character in combination["string"]:
            if character not in node:
                node[character] = {}
            node = node[character]
        node["terminal"] = {"handler":combination["handler"]}
    tokens = []
    while index<length:
        character = string[index]
        if character in fsm:
            node = fsm[character]
            if index+1<length:
                lookahead = string[index+1]
                if lookahead in node:
                    index += 1
                    node = node[lookahead]
            if "terminal" in node:
                terminal = node["terminal"]
                if "handler" in terminal:
                    result = terminal["handler"](string,index)
                    index = result["index"]
                if "type" in result:
                    token = {"type":result["type"],"string":result["string"]}
                    if "value" in result:
                        token["value"] = result["value"]
                    tokens.append(token)
    return tokens
        #operator, separator
def parse(string):
    tokens = scan(string,0)
    index = 0
    while index<len(tokens):
        pass

def eat_whitespace(string,index):
    while index<len(string) and is_whitespace(string[index]):
        index += 1
    return {"index":index}

def parse_identifier(string,index):
    start = index
    index += 1
    while index<len(string) and is_identifier_char(string[index]):
        index += 1
    return {"index":index,"position":start,"string":string[start:index],"type":"identifier","value":string[start:index]}

def is_digit(character):
    if character in u"0123456789":
        return True
    return False

def is_identifier_char(character):
    if character in u"_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        return True
    return False

def is_identifier_start(character):
    if character in u"_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
        return True
    return False

def is_whitespace(character):
    if character in u" \n\r\t":
        return True
    return False
    

class TestHandler(AdminHandler):
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
        #T = FSMBuilder()
        #T.parse()
        #logging.info(T.fsm)            
                
        #self.response.write(T.fsm)
        self.context["response"] = scan("_test01 // test3\ntest2\r /* \n test4 * / */   test5='test6 ';",0)
        self.render_response('/javascript-test.html')
        
