# -*- coding: UTF-8 -*-
from ailete619.beakon import handlers, http, log, users
import fetch
import jse
import scrap
import secrets
import webapp2

class HomeHandler(handlers.WithSessionHandler):
    def get(self,**kwargs):
        self.render_response('pascra.html')

config = {}
config['webapp2_extras.auth'] = {
                                'user_model': 'ailete619.beakon.users.Profile',
                                'user_attributes': ['access','email','login','name']
                                }
config['webapp2_extras.sessions'] = {
                                    'secret_key': secrets.scraper_key,
                                    }

app = webapp2.WSGIApplication([
                               webapp2.Route('/cache/delete', fetch.CacheDeleteHandler),
                               webapp2.Route('/fetch', fetch.Handler),
                               webapp2.Route('/fetch/test', fetch.TestHandler),
                               webapp2.Route('/javascript_engine/test', jse.TestHandler),
                               webapp2.Route('/scrap', scrap.ScrapingHandler),
                               webapp2.Route('/scrap/source', scrap.SourceHandler),
                               webapp2.Route('/scrap/test', scrap.TestHandler),
                               webapp2.Route('/scrap/help', scrap.HelpHandler),
                               webapp2.Route('/users/access/denied', users.AccessDeniedHandler),
                               webapp2.Route('/users/delete', users.DeleteHandler),
                               webapp2.Route('/users/google/admin/signup', users.GoogleAdminSignUpHandler),
                               webapp2.Route('/users/list', users.ListHandler),
                               webapp2.Route('/users/edit', users.EditHandler),
                               webapp2.Route('/users/signin', users.SignInHandler),
                               webapp2.Route('/users/signout', users.SignOutHandler),
                               webapp2.Route(r'/internal/item', scrap.ItemHandler),
                               webapp2.Route(r'/internal/list', scrap.ListHandler),
                               ('/?', HomeHandler)
                              ],
                              config=config,
                              debug=False)
app.error_handlers[401] = http.Error_401
app.error_handlers[404] = http.Error_404
#app.error_handlers[500] = http.Error_500
