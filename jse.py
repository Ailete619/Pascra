
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

class AST(object):
    def evaluate(self):
        pass

class Parser(object):
    def process(self,tokens,pos):
        pass

class Option(Parser):
    def __init__(self,parser):
        self.parser = parser
    def process(self,tokens,pos):
        result = self.parser.__process__(tokens,pos)
        if result:
            return result
        else:
            return None

class Scope(dict):
    def __init__(self, outer=None):
        self.outer
    def find(self,var):
        return self if (var in self) else self.outer.find(var)

def scan(string,position):
    def is_digit(character):
        if character in u"0123456789":
            return True
        return False
    def is_end_of_line(string,position):
        if string[position]=="\n":
            return 1
        elif string[position]=="\r":
            if string[position+1]=="\n":
                return 2
            return 1
        return 0
    def is_identifier_char(character):
        if character in u"_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
            return True
        return False
    def is_whitespace(character):
        if character in u" \f\t\n\r":
            return True
        return False
    def scan_identifier(position):
        start = position
        position += 1
        while position<len(string) and is_identifier_char(string[position]):
            position += 1
        return {"position":position,"start":start,"string":string[start:position],"type":"identifier","value":string[start:position]}
    def scan_multiline_comment(position):
        while position<len(string):
            position +=1
            if string[position]=="*":
                position +=1
                if string[position]=="/":
                    break
        position += 1
        return {"position":position}
    def scan_number(position):
        start = position
        position += 1
        while position<len(string) and is_digit(string[position]):
            position += 1
        if string[position]==".":
            position += 1
            while position<len(string) and is_digit(string[position]):
                position += 1
        return {"position":position,"start":start,"string":string[start:position],"type":"number","value":float(string[start:position])}
    def scan_operator(position):
        """fsm = {}
        for operator in ["+","-","*","/","%","++","--","=","+=","-=","*=","/=","%=","==","===","!=","!==","<","<=",">",">=","&&","||","!","&","|","^","~","<<",">>",">>>"]:
            node = fsm
            for character in operator:
                if character not in node:
                    node[character] = {}
                node = node[character]
            node["terminal"] = True
        logging.info("operator fsm="+str(fsm))
        """
        fsm = {
               '!':{'terminal':True},
                    '=':{'terminal':True,
                         '=':{'terminal':True}},
               '%':{'terminal':True,
                    '=':{'terminal':True}},
               '&':{'terminal':True,
                    '&':{'terminal':True}},
               '+':{'terminal':True,
                    '+':{'terminal':True},
                    '=':{'terminal':True}},
               '*':{'terminal':True,
                  '=':{'terminal':True}},
               '-':{'terminal':True,
                    '=':{'terminal':True},
                    '-':{'terminal':True}},
               '/':{'terminal':True,
                    '=':{'terminal':True}},
               '|':{'terminal':True,
                    '|':{'terminal':True}},
               '~':{'terminal':True},
               '^':{'terminal':True},
               '=':{'terminal':True,
                    '=':{'terminal':True,
                         '=':{'terminal':True}}},
               '<':{'terminal':True,
                    '=':{'terminal':True},
                    '<':{'terminal':True}},
                '>':{'terminal':True,
                     '=':{'terminal':True},
                     '>':{'terminal':True,
                          '>':{'terminal':True}}}
               }
        start = position
        node = fsm
        character = string[position]
        logging.info("    character='"+str(character)+"'")
        while position<len(string) and character in node:
            node = node[character]
            position += 1
            character = string[position]
        if "terminal" in node:
            return {"position":position,"start":start,"string":string[start:position],"type":"operator"}
        else:
            return {"position":position,"start":start,"type":"error"}
    def scan_separator(position):
        start = position
        position += 1
        return {"position":position,"start":start,"string":string[start:position],"type":"separator"}
    def scan_single_line_comment(position):
        offset = is_end_of_line(string,position)
        while position<len(string) and offset==0:
            position += 1
            offset = is_end_of_line(string,position)
        position += offset
        return {"position":position}
    def scan_string(position):
        quote = string[position]
        start = position
        position = position+1
        while position<len(string) and string[position]!=quote:
            position += 1
        position +=1
        return {"position":position,"start":start,"string":string[start:position],"type":"string","value":string[(start+1):(position-1)]}
    def scan_whitespace(position):
        position += 1
        character = string[position]
        while position<len(string) and is_whitespace(character):
            position += 1
            character = string[position]
        return {"position":position}

    length = len(string)
    fsm = {}
    for char_range in [
                       {"list":"_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ","handler":scan_identifier},
                       {"list":"\'\"","handler":scan_string},
                       {"list":"0123456789","handler":scan_number},
                       {"list":" \n\r\t","handler":scan_whitespace},
                       {"list":"!%&=-^|@+*<>?/\\","handler":scan_operator},
                       {"list":",.:;()[]{}","handler":scan_separator}
                       ]:
        node = fsm
        for character in char_range["list"]:
            if character not in node:
                node[character] = {}
                node[character]["terminal"] = {"handler":char_range["handler"]}
    for combination in [
                        {"string":"//","handler":scan_single_line_comment},
                        {"string":"/*","handler":scan_multiline_comment},
                        ]:
        node = fsm
        for character in combination["string"]:
            if character not in node:
                node[character] = {}
            node = node[character]
        node["terminal"] = {"handler":combination["handler"]}

    while position<len(string):
        character = string[position]
        if character in fsm:
            node = fsm[character]
            if position+1<length:
                lookahead = string[position+1]
                if lookahead in node:
                    position += 1
                    node = node[lookahead]
            if "terminal" in node:
                terminal = node["terminal"]
                if "handler" in terminal:
                    result = terminal["handler"](position)
                    position = result["position"]
                if "type" in result:
                    return result
def parse(string):
    def parse_assignment(index,identifier):
        token = scan(string,index)
        index=token["position"]
        logging.info(token)
        if token["type"]=="number":
            token = scan(string,index)
            index=token["position"]
            logging.info(token)
            if token["type"]=="separator" and token["string"]==";":
                logging.info("goal")
                
        pass
    global_env = Scope()
    index = 0
    while index<len(string):
        token = scan(string,index)
        index = token["position"]
        logging.info(token)
        if token["type"]=="identifier":
            if token["string"]=="var":
                token = scan(string,index)
                index=token["position"]
                logging.info(token)
                if token["type"]=="identifier":
                    Scope.update({token["string"]:None})
                    token = scan(string,index)
                    index=token["position"]
                    logging.info(token)
                    if token["type"]=="operator":
                        if token["string"]=="=":
                            parse_assignment(index)
                    return "var defined"
                    break

class TestHandler(AdminHandler):        
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
        self.context["response"] = parse(js_string)
        self.render_response('/javascript-test.html')
        
