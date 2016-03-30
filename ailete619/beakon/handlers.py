# -*- coding: utf-8 -*-
'''

@author: Loic LE TEXIER
'''
from config import locale
from config import settings
import importlib
import logging
import webapp2
from webapp2_extras import auth, jinja2, sessions
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError

class BaseHandler(webapp2.RequestHandler):
    @webapp2.cached_property
    def auth(self):
        """Shortcut to access the auth instance as a property."""
        return auth.get_auth()
    @webapp2.cached_property
    def jinja2(self):
        """ Returns a Jinja2 renderer cached in the app registry. """
        return jinja2.get_jinja2(app=self.app)
    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session(backend="datastore")
    @webapp2.cached_property
    def user(self):
        """Shortcut to access the current logged in user.
        
        Unlike user_info, it fetches information from the persistence layer and
        returns an instance of the underlying model.
        
        :returns
          The instance of the user model associated to the logged in user.
        """
        u = self.user_info
        return self.user_model.get_by_id(u['user_id']) if u else None
    @webapp2.cached_property
    def user_info(self):
        """Shortcut to access a subset of the user attributes that are stored
        in the session.
        
        The list of attributes to store in the session is specified in
          config['webapp2_extras.auth']['user_attributes'].
        :returns
          A dictionary with most user information
        """
        return self.auth.get_user_by_session()
    @webapp2.cached_property
    def user_model(self):
        """Returns the implementation of the user model.
        
        It is consistent with config['webapp2_extras.auth']['user_model'], if set.
        """   
        return self.auth.store.user_model
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
                        self.context["locale"] = locale[language_key]
                        return
        self.context["locale"] = locale[default_locale]
    # this is needed for webapp2 sessions to work
    def dispatch(self):
        self.context = {}
        self.set_locale(self.request.headers.get('accept_language'))
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)
        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)
    def render_response(self, _template, template_context=None):
        """ Renders a template and writes the result to the response. """
        if not template_context:
            template_context={}
        template_context['user'] = self.user_info
        logging.info(self.user_info)
        template_context.update(self.context)
        rv = self.jinja2.render_template(_template, **template_context)
        self.response.write(rv)
    def signout(self):
        self.auth.unset_session()

class UserHandler(BaseHandler):
    def get(self,**kwargs):
        auth = self.auth
        if not auth.get_user_by_session():
            self.redirect("/users/access/denied")
    def post(self,**kwargs):
        auth = self.auth
        if not auth.get_user_by_session():
            self.redirect("/users/access/denied")

class DispatchHandler(BaseHandler):
    def get_command(self, **kwargs):
        logging.info(self.__class__.__name__+".get_command("+str(kwargs)+")")
        if "domain" not in kwargs or "command" not in kwargs:
            if self.request.path=="/":
                kwargs["type"] = "system"
                kwargs["domain"] = "users"
                kwargs["command"] = "homepage"
            else:
                logging.warning(self.__class__.__name__+".get_command("+str(kwargs)+") : no command to dispatch!")
                return

        if "subcommand" in kwargs:
            kwargs["command"] += kwargs["subcommand"]
            del kwargs["subcommand"]

        try:
            if "type" in kwargs and kwargs["type"]=="system":
                module_name = "ailete619.beakon."+kwargs["domain"]+".commands"
            else:
                module_name = settings["application_domain"]+"."+kwargs["domain"]+".commands"
            module = importlib.import_module(module_name)
            return getattr(module, kwargs["command"])(self)
        except Exception as e:
            logging.info(e)
            logging.warning(self.__class__.__name__+".get_command("+str(kwargs)+") : command not found!")
        #    raise e
        
    def get(self,**kwargs):
        logging.info("cookies="+str(self.request.cookies))
        auth = self.auth
        logging.info("handler get")
        logging.info("self.user="+str(self.user))
        logging.info("self.user_info="+str(self.user_info))
        logging.info("auth._user="+str(auth._user))
        logging.info("auth.get_user_by_session()="+str(auth.get_user_by_session()))
        logging.info("handler")
        command = self.get_command(**kwargs)
        if command:
            command.process_get(**kwargs)
        else:
            logging.warning(self.__class__.__name__+".get("+str(kwargs)+") : no command to dispatch!")
    def post(self,**kwargs):
        logging.info(self.request.cookies.keys())
        auth = self.auth
        logging.info("handler post")
        logging.info("self.user="+str(self.user))
        logging.info("self.user_info="+str(self.user_info))
        logging.info("auth._user="+str(auth._user))
        logging.info("auth.get_user_by_session()="+str(auth.get_user_by_session()))
        logging.info("handler")
        command = self.get_command(**kwargs)
        if command:
            command.process_post(**kwargs)
        else:
            logging.warning(self.__class__.__name__+".post("+str(kwargs)+") : no command to dispatch!")

