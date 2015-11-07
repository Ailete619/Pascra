# -*- coding: UTF-8 -*-
from google.appengine.api import taskqueue, users
import logging
import webapp2
from webapp2_extras import jinja2

class BaseHandler(webapp2.RequestHandler):
    @webapp2.cached_property
    def jinja2(self):
        """ Returns a Jinja2 renderer cached in the app registry. """
        return jinja2.get_jinja2(app=self.app)
    def render_response(self, _template, **context):
        """ Renders a template and writes the result to the response. """
        rv = self.jinja2.render_template(_template, **context)
        self.response.write(rv)

class MiscHandler(BaseHandler):
    def get(self,**kwargs):
        self.render_response('/pascra.html', **kwargs)
    def post(self,**kwargs):
        self.render_response('/pascra.html', **kwargs)

class ScrappingHandler(BaseHandler):
    def get(self,**kwargs):
        kwargs["method"]="get"
        self.validateAndDispatch(**kwargs)
    def post(self,**kwargs):
        kwargs["method"]="post"
        self.validateAndDispatch(**kwargs)

config = {}

app = webapp2.WSGIApplication([
                               webapp2.Route(r'/scrap/page', ScrappingHandler),
                               ('.*', MiscHandler)
                              ],
                              config=config,
                              debug=False)
