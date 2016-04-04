# -*- coding: utf-8 -*-
'''

@author: Loic LE TEXIER
'''
from google.appengine.api import users
from google.appengine.ext import ndb
from handlers import AdminHandler, BaseHandler, UserHandler
import logging
import time
from webapp2_extras import security
import webapp2_extras.appengine.auth.models
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError

import sys
from google.appengine.ext import ndb
sys.modules['ndb'] = ndb

class Profile(webapp2_extras.appengine.auth.models.User):
    access = ndb.StringProperty(default="user")
    email = ndb.StringProperty()
    google_user_id = ndb.StringProperty()
    login = ndb.StringProperty()
    name = ndb.StringProperty()
    password = ndb.StringProperty()
    @classmethod
    def get_by_auth_token(cls, user_id, token, subject='auth'):
        """Returns a user object based on a user ID and token.
        
        :param user_id:
            The user_id of the requesting user.
        :param token:
            The token string to be verified.
        :returns:
            A tuple ``(User, timestamp)``, with a user object and
            the token timestamp, or ``(None, None)`` if both were not found.
        """
        token_key = cls.token_model.get_key(user_id, subject, token)
        user_key = ndb.Key(cls, user_id)
        # Use get_multi() to save a RPC call.
        valid_token, user = ndb.get_multi([token_key, user_key])
        if valid_token and user:
            timestamp = int(time.mktime(valid_token.created.timetuple()))
            return user, timestamp
        
        return None, None
    @classmethod
    def deleteAll(cls, profile_key_list):
        # delete all the permanent user accounts in the list
        for profile_key in profile_key_list:
            ndb.Key(urlsafe=profile_key).delete()
    @classmethod
    def find_current_google_user_profile(cls):
        # return the profile for the current google user, if the current user is a google user
        user = users.get_current_user()
        if user:
            q = ndb.gql("SELECT * FROM User WHERE google_user_id = :1", user.user_id())
            return q.get()
    @classmethod
    def find_current_user_profile(cls, login):
        # return the profile for this login if it exists
        q = ndb.gql("SELECT * FROM User WHERE login = :1", login)
        return q.get()
    def set_password(self, raw_password):
        """Sets the password for the current user
        
        :param raw_password:
            The raw password which will be hashed and stored
        """
        self.password = security.generate_password_hash(raw_password, length=12)
 
class AccessDeniedHandler(BaseHandler):
    def get(self,**kwargs):
        self.render_response('/users/access-denied.html')

class DeleteHandler(AdminHandler):
    def finish(self,**kwargs):
        if "selected_user_profile_list" in kwargs:
            Profile.deleteAll(kwargs["selected_user_profile_list"])
        #elif "selected_new_profile_list" in kwargs:
        #    NewUser.deleteAll(kwargs["selected_new_profile_list"])
        else:
            logging.error("tica.users.delegates.delete.process(): no list of dictionaries or keywords found!")

class EditHandler(AdminHandler):
    def get(self):
        user_id = self.request.get("id")
        if user_id:
            key = ndb.Key(urlsafe=user_id)
            if key:
                profile = key.get()
                self.context["profile"] = profile
        self.render_response('/users/edit.html')
    def post(self):
        id = self.request.get("userID")
        access=self.request.get("userAccessLevel")
        email=self.request.get("userEmail")
        login=self.request.get("userLogin")
        if not login:
            login = email
        name=self.request.get("userName")
        password=self.request.get("userPassword")
        profile = None
        if id:
            key = ndb.Key(urlsafe=id)
            if key:
                profile = key.get()
                profile.access=access
                profile.email=email
                profile.login=login
                profile.name=name
                if password:
                    profile.password=password
                profile.put()
            else:
                self.context["error_message"] = self.context["locale"]["users"]["not_found"]
        else:
            access=self.request.get("userAccessLevel")
            email=self.request.get("userEmail")
            login=self.request.get("userLogin")
            if not login:
                login = email
            name=self.request.get("userName")
            password=self.request.get("userPassword")
            unique_properties = ['login']
            user_data = self.user_model.create_user(login,
              unique_properties,
              access=access, email=email, login=login, name=name, password_raw=password,
              verified=True)
            if user_data[0]: #user_data is a tuple
                profile = user_data[0]
            else:
                self.context["error_message"] = self.context["locale"]["users"]["could_not_create"]
        self.context["profile"] = profile
        self.render_response('/users/edit.html')

class GoogleSignInHandler(BaseHandler):
    def get(self):
        # checks if the current user has a Google user profile available
        google_user = users.get_current_user()
        
        # if there is no Google user profile, the user is redirected to an access denied page
        if not google_user:
            logging.warning(self.__class__.__name__+".get() : no Google user signed in!")
            self.redirect(users.create_login_url("/"))
            return

        # checks if the current user has a profile registered with our application
        profile = Profile.query(Profile.google_user_id == google_user.user_id()).get()
        # if there is no user profile,  
        if not profile:
            logging.warning(self.__class__.__name__+".get() : no profile for user "+str(google_user.email()))
            # maybe he/she is a Google admin for this application
            if users.is_current_user_admin():
                # in that case, a default admin profile is created automatically for our Google admin user to avoid the hen and egg problem, and also to protect the admin from being logged out by application level users!
                unique_properties = ['login']
                login = "Root"
                user_data = self.user_model.create_user(login,
                  unique_properties,
                  access="admin", email=google_user.email(), google_user_id=google_user.user_id(), login=login, name=login, password_raw=login,
                  verified=True)
                if not user_data[0]: #user_data is a tuple
                  logging.info('Unable to create user for email  because of  duplicate keys ')
                  return
                logging.info(user_data)
                user = user_data[1]
                user_id = user.get_id()
                # store user data in the session
                self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
            else:
                # if the user is not a Google admin either, a warning is logged on the Google dashboard with the user information ... And the user is redirected to an access denied page
                # TO DO : a real connection log in the application
                return self.redirect('users.create_login_url("/")')
        else:
            # if there is a user profile but the user is the Google admin for this application but his/her access level has been set to "user, we set it back to "admin"
            if profile.access=="user" and users.is_current_user_admin():
                profile.access = "admin"
                profile.put()
        self.redirect("/")
 
class ListHandler(AdminHandler):
    def get(self):
        self.context["user_profile_list"] = Profile.query()
        self.render_response('/users/list.html')

class SignInHandler(BaseHandler):
    def get(self):
        self.render_response('/users/signin.html',self.context)
    def post(self):
        login = self.request.get('userLogin')
        password = self.request.get('userPassword')
        try:
            user = self.auth.get_user_by_password(login, password, remember=True)
            self.render_response('/users/signin.html',self.context)
        except (InvalidAuthIdError, InvalidPasswordError) as e:
            logging.info('Login failed for user %s because of %s', login, type(e))
            self.redirect("/users/access/denied")
 
class SignOutHandler(BaseHandler):
    def get(self):
        self.auth.unset_session()
        self.redirect("/")
