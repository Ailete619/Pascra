# -*- coding: utf-8 -*-
'''

@author: Loic LE TEXIER
'''
from config import locale
import external
from google.appengine.api import taskqueue, urlfetch, users
import json
import logging
import urllib
from users import Profile

class BaseCommand(object):
    @classmethod
    def addTask(cls, **kwargs):
        logging.info(cls.__name__+".addTask("+str(kwargs)+")")
        if "handler" in kwargs:
            del kwargs["handler"]
        taskqueue.add(url='/internal/'+kwargs["domain"]+'/'+kwargs["command"],queue_name=kwargs["domain"],params={"json":json.dumps(kwargs)})
    @classmethod
    def sendRequest(cls, url, method=None, data=None, headers=None):
        http_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        if headers is not None:
            http_headers.update(headers)
        post_data_encoded = urllib.urlencode(data)
        if method=="get":
            method = urlfetch.GET
        elif method=="post":
            method = urlfetch.POST
        else:
            if data == None:
                method = urlfetch.GET
            else:
                method = urlfetch.POST
        return urlfetch.fetch(url=url,payload=post_data_encoded,method=method,headers=http_headers)
    @classmethod
    def parse_accept_language(cls, accept_language):
        languages = accept_language.split(",")
        language_pairs = []
        for language in languages:
            if language.split(";")[0] == language:
                # no q => q = 1
                language_pairs.append((language.strip(), "1"))
            else:
                locale = language.split(";")[0].strip()
                q = language.split(";")[1].split("=")[1]
                language_pairs.append((locale, q))
        return language_pairs
    def set_locale(self, accept_language):
        default_locale = 'en'
        if accept_language:
            language_pairs = self.parse_accept_language(accept_language)
            for pair in language_pairs:
                for language_key in locale.keys():
                    # pair[0] is locale, pair[1] is q value
                    if pair[0].replace('-', '_').lower().startswith(language_key.lower()):
                        self.response["locale"] = locale[language_key]
                        return
        self.response["locale"] = locale[default_locale]
    def create_login_url(self,url):
        return users.create_login_url(url)
    def create_logout_url(self,url):
        return users.create_logout_url(url)
    def finish(self,**kwargs):
        pass
    def get(self,**kwargs):
        pass
    def post(self,**kwargs):
        pass
    def prepare(self,**kwargs):
        pass
    def process(self,**kwargs):
        pass
    def process_get(self,**kwargs):
        self.process(**kwargs)
        self.prepare(**kwargs)
        self.get(**kwargs)
        self.finish(**kwargs)
    def process_post(self,**kwargs):
        self.process(**kwargs)
        self.prepare(**kwargs)
        self.post(**kwargs)
        self.finish(**kwargs)

class Command(BaseCommand):
    def __init__(self, GAE_handler):
        self.GAE_handler = GAE_handler
        self.auth = GAE_handler.auth
        self.response = {}
        self.set_locale(self.GAE_handler.request.headers.get('accept_language'))
    def redirect(self,uri):
        self.GAE_handler.redirect(uri, abort=True)
    def render_response(self,uri):
        self.GAE_handler.render_response(uri,self.response)

class AnonymousCommand(Command):
    def process(self,**kwargs):
        pass

class ExternalCommand(Command):
    @classmethod
    def sendExternalDataRequest(cls, url, method=None, data=None, headers={}, edr_id=None):
        edr = external.DataRequest()
        if url:
            edr.referer = url
        else:
            logging.warning(cls.__name__+".sendExternalDataRequest(): no url !")
        edr.put()
        headers["Set-Cookie"]= "edr_id="+edr.key.urlsafe()+"; path=/"
        return cls.sendRequest(url=url, method=method, data=data, headers=headers)
    def process(self,**kwargs):
        logging.info(self.__class__.__name__+".process("+str(kwargs)+")")
        #for key, value in self.GAE_handler.request.headers.iteritems():
        #    logging.info(key+"="+value)
        referer = self.GAE_handler.request.referer
        ip_address = self.GAE_handler.request.remote_addr
        #cookies = {}
        #raw_cookies = self.GAE_handler.request.headers.get("Cookie")
        #if raw_cookies:
        #    for cookie in raw_cookies.split(";"):
        #        name, value = cookie.split("=")
        #        for name, value in cookie.split("="):
        #            cookies[name] = value
        edr_id = self.GAE_handler.request.cookies.get("edr_id")
        logging.info("    edr_id="+str(edr_id))
        if edr_id:
            logging.info("    edr_eof="+str(self.GAE_handler.request.headers.get("edr_eof")))
            logging.info("    referer="+referer)
            if external.DataRequest.validate(edr_id, referer, self.GAE_handler.request.headers.get("edr_eof")):
                pass
            else:
                logging.warning(self.__class__.__name__+".process() : invalid external request !")
                return
        else:
            edr_id = self.GAE_handler.request.headers.get("set_edr_id")
            if not edr_id:
                logging.warning(self.__class__.__name__+".process() : no request id !")

        request = self.GAE_handler.request
        arguments = {name:self.GAE_handler.request.get(name) for name in self.GAE_handler.request.arguments() if name != "type"}
        if "json" in arguments:
            arguments["json"] = json.loads(arguments["json"])
        self.response.update(arguments)

class GoogleUserCommand(Command):
    def validate_user(self,**kwargs):
        request = self.GAE_handler.request
        # checks if the current user has a Google user profile available
        user = users.get_current_user()
        
        # if there is no Google user profile, the user is redirected to an access denied page
        if not user:
            logging.warning(self.__class__.__name__+".process() : no Google user signed in!")
            self.redirect('/system/users/access/denied')
            

        # checks if the current user has a profile registered with our application
        profile = Profile.query(Profile.google_user_id == user.user_id()).get()
        # if there is no user profile,  
        if not profile:
            # maybe the user profile is a new user profile and needs to be validated ...
            # or if the user is not a new user maybe he/she is a Google admin for this application
            if users.is_current_user_admin():
                # in that case, a default admin profile is created automatically for our Google admin user to avoid the hen and egg problem, and also to protect the admin from being logged out by application level users!
                profile = Profile(access="admin",email=user.email(),name="Root",google_user_id=user.user_id())
                profile.put()
            else:
                # if the user is not a Google admin either, a warning is logged on the Google dashboard with the user information ... And the user is redirected to an access denied page
                # TO DO : a real connection log in the application
                logging.warning(self.__class__.__name__+".process() : unregistered user (id="+user.user_id()+"/email="+user.email()+"/ip address="+request.remote_addr+") tried to connect!")
                return self.redirect('/system/users/access/denied')
        else:
            # if there is a user profile but the user is the Google admin for this application but his/her access level has been set to "user, we set it back to "admin"
            if profile.access=="user" and users.is_current_user_admin():
                profile.access = "admin"
                profile.put()
        self.response["access"] = profile.access
        self.response["email"] = profile.email
        self.response["logout"] = users.create_logout_url('/')
        self.response["username"] = profile.name
        return True
    def process(self,**kwargs):
        if self.validate_user(**kwargs):
            request = self.GAE_handler.request
            arguments = {name:request.get(name) for name in request.arguments() if name != "type"}
            logging.info("arguments="+str(arguments))
            if "json" in arguments:
                arguments = json.loads(arguments["json"])
            logging.info("arguments="+str(arguments))
            self.response.update(arguments)

class GoogleAdminCommand(GoogleUserCommand):
    def validate_user(self,**kwargs):
        validated = super(GoogleAdminCommand, self).validate_user(**kwargs)
        # if the user does not have "admin" access level, he/she is redirected to an access denied page
        if self.response["access"]!="admin":
            logging.warning(self.__class__.__name__+".validate_user() : registered user "+self.response["username"]+" ("+self.response["email"]+") tried to access an \"admin\" access level command!")
            self.redirect('/system/users/access/denied')
        return validated
            
class InternalCommand(Command):
    def process(self,**kwargs):
        request = self.GAE_handler.request

        #logging.info(request.headers)
        if False:
            logging.warning(self.__class__.__name__+".process() : all internal commands must be called from the same GAE app!")

        arguments = {name:request.get(name) for name in request.arguments()}
        if "json" in arguments:
            arguments = json.loads(arguments["json"])
        self.response.update(arguments)
        
class UserCommand(Command):
    def process(self,**kwargs):
        request = self.GAE_handler.request
        auth = self.GAE_handler.auth
        if not auth.get_user_by_session():
            self.GAE_handler.redirect("/users/access/denied")

class AdminCommand(UserCommand):
    def process(self,**kwargs):
        super(AdminCommand, self).process(**kwargs)
        user = self.GAE_handler.user_info
        if not user or user["access"]!="admin":
            self.GAE_handler.redirect("/users/access/denied")

