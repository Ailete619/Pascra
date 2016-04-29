# -*- coding: UTF-8 -*-
import ailete619.beakon.handlers
import ailete619.beakon.users
import fetch
from google.appengine.api import taskqueue
import jse
import logging
import webapp2
import scrap

class HomeHandler(ailete619.beakon.handlers.BaseHandler):
    def get(self,**kwargs):
        self.render_response('pascra.html')

class ScrapingHandler(ailete619.beakon.handlers.BaseHandler):
    def get(self,**kwargs):
        self.render_response('/pascra.html')
    def post(self,**kwargs):
        #logging.info(self.request.headers)
        #logging.info(self.request.get("json"))
        parameters = {}
        parameters['referer_url'] = self.request.url
        if "Set-Cookie" in self.request.headers:
            parameters['response_cookies'] = self.request.headers["Set-Cookie"]
        parameters['response_url'] = self.request.headers.get("Referer")
        parameters['json'] = self.request.get("json")
        taskqueue.add(url='/internal/list',queue_name='scraping',params=parameters)
        self.response.set_status(200)
        
config = {}
config['webapp2_extras.auth'] = {
                                'user_model': 'ailete619.beakon.users.Profile',
                                'user_attributes': ['access','email','login','name']
                                }
config['webapp2_extras.sessions'] = {
                                    'secret_key': 'my-super-secret-key',
                                    }

app = webapp2.WSGIApplication([
                               webapp2.Route('/cache/delete', fetch.CacheDeleteHandler),
                               webapp2.Route('/fetch', fetch.Handler),
                               webapp2.Route('/fetch/test', fetch.TestHandler),
                               webapp2.Route('/javascript_engine/test', jse.TestHandler),
                               webapp2.Route('/scrap', ScrapingHandler),
                               webapp2.Route('/scrap/source', scrap.SourceHandler),
                               webapp2.Route('/scrap/test', scrap.TestHandler),
                               webapp2.Route('/scrap/help', scrap.HelpHandler),
                               webapp2.Route('/users/access/denied', ailete619.beakon.users.AccessDeniedHandler),
                               webapp2.Route('/users/delete', ailete619.beakon.users.DeleteHandler),
                               webapp2.Route('/users/google/signin', ailete619.beakon.users.GoogleSignInHandler),
                               webapp2.Route('/users/list', ailete619.beakon.users.ListHandler),
                               webapp2.Route('/users/edit', ailete619.beakon.users.EditHandler),
                               webapp2.Route('/users/signin', ailete619.beakon.users.SignInHandler),
                               webapp2.Route('/users/signout', ailete619.beakon.users.SignOutHandler),
                               webapp2.Route(r'/internal/item', scrap.ItemHandler),
                               webapp2.Route(r'/internal/list', scrap.ListHandler),
                               ('/?', HomeHandler)
                              ],
                              config=config,
                              debug=False)
