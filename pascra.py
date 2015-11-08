# -*- coding: UTF-8 -*-
from google.appengine.api import taskqueue, users
import json
import logging
from scrap import PageScraper
import urllib
import urllib2
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

class PostTestingHandler(BaseHandler):
    def get(self,**kwargs):
        self.render_response('/pascra_post.html', **kwargs)
    def post(self,**kwargs):
        testdata = {"url":"http://www6.nhk.or.jp/kokusaihoudou/archive/archive.html?i=151106","encoding":"utf-8","selectors":["nav>ul>li>a"]}
        url = self.request.get("url")
        if not url:
            logging.error("No URL to scrap!")
        encoding = self.request.get("encoding")
        selectors = self.request.get("selectors")
        selectors = selectors.splitlines()
        #response = requests.post("/scrap/page", data={'url': url, 'encoding': encoding, 'selectors': selectors})
        http_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        post_data_encoded = urllib.urlencode({'json':json.dumps({'url': url, 'encoding': encoding, 'selectors': selectors})})
        request_object = urllib2.Request("https://pascra619.appspot.com/scrap/page", post_data_encoded,http_headers)
        response = urllib2.urlopen(request_object)
        logging.info('response')
        logging.info(response)
        

class ScrappingHandler(BaseHandler):
    def get(self,**kwargs):
        self.render_response('/pascra.html', **kwargs)
    def post(self,**kwargs):
        response = PageScraper.fetch(self.request.get('json'))
        logging.info('response')
        logging.info(json.dumps(response))
        self.response.write(json.dumps(response))
        

config = {}

app = webapp2.WSGIApplication([
                               webapp2.Route(r'/scrap/page/post', PostTestingHandler),
                               webapp2.Route(r'/scrap/page', ScrappingHandler),
                               ('.*', MiscHandler)
                              ],
                              config=config,
                              debug=False)
