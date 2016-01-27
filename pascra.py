# -*- coding: UTF-8 -*-
from google.appengine.api import taskqueue, users
import json
import logging
from scrap import WebsiteScraper
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

class RequestTestingHandler(BaseHandler):
    def get(self,**kwargs):
        test_kukkiapple_order_scraping =   {
                                             "login":{"url":"https://apple.kukkia.jp/bin/login.php","login":{"name":"login_id","value":"kukkia"},"password":{"name":"login_pw","value":"kukkiapple"},"fields":[{"name":"bst","value":"1024"},{"name":"bsy","value":"1280"}]},
                                             "scrap_list":[
                                                             {
                                                              "encoding":"utf-8",
                                                              "fields":[{"name":"cmd","value":"form"},
                                                                        {"name":"flg","value":"0"},
                                                                        {"name":"bst","value":"1024"},
                                                                        {"name":"bsy","value":"1280"}],
                                                              "for_field":{"name":"pi_id","values":["1"]},
                                                              "selectors":{
                                                                           "order_date":{"string":"input#pi_date","extractor":{"type":"attribute","name":"value"}},
                                                                           "customer_code":{"string":"input#pi_cus_code","extractor":{"type":"attribute","name":"value"}},
                                                                           "customer_name":{"string":"input#pi_customer_name","extractor":{"type":"attribute","name":"value"}},
                                                                           "customer_address":{"string":"textarea#pi_sold_to","extractor":{"type":"method","name":"text"}},
                                                                           "shipping_address":{"string":"textarea#pi_ship_to","extractor":{"type":"method","name":"text"}},
                                                                           "order_delivery_date":{"string":"input#pi_delivery_date","extractor":{"type":"attribute","name":"value"}},
                                                                           "order_delivery_way":{"string":"input#pi_way_of_deli","extractor":{"type":"attribute","name":"value"}},
                                                                           "order_terms":{"string":"input#pi_terms","extractor":{"type":"attribute","name":"value"}},
                                                                           "exchange_rate":{"string":"input#pi_rate","extractor":{"type":"attribute","name":"value"}},
                                                                           "subtotal":{"string":"td#sub_total","extractor":{"type":"text"}},
                                                                           "discount_percentage":{"string":"input#discount_par","extractor":{"type":"attribute","name":"value"}},
                                                                           "discount":{"string":"input#pi_discount","extractor":{"type":"attribute","name":"value"}},
                                                                           "shipping_cost":{"string":"input#pi_shipping_cost","extractor":{"type":"attribute","name":"value"}},
                                                                           "bank_handling_charge":{"string":"input#pi_bank_handling_charge","extractor":{"type":"attribute","name":"value"}},
                                                                           "total":{"string":"td#grand_total","extractor":{"type":"text"}},
                                                                           "memo":{"string":"textarea#pi_memo","extractor":{"type":"method","name":"text"}},
                                                                           },
                                                              "tabular_selectors":{
                                                                                   "order_lines":{"line_selector":"div#ajax_area tr",
                                                                                                  "cell_selectors":[
                                                                                                                    {"name":"line_number","string":"td:first-child","extractor":{"type":"text"}},
                                                                                                                    {"name":"reference","string":"td:nth-child(2) input[type=text]","extractor":{"type":"attribute","name":"value"}},
                                                                                                                    {"name":"name","string":"td:nth-child(2) span","extractor":{"type":"text"}},
                                                                                                                    {"name":"warehouse","string":"td:nth-child(3) select option[selected]","extractor":{"type":"text"}},
                                                                                                                    {"name":"price","string":"td:nth-child(4) input","extractor":{"type":"attribute","name":"value"}},
                                                                                                                    {"name":"quantity","string":"td:nth-child(5) input","extractor":{"type":"attribute","name":"value"}},
                                                                                                                    {"name":"backorder","string":"td:nth-child(6) input","extractor":{"type":"attribute","name":"value"}},
                                                                                                                    {"name":"amount","string":"td:nth-child(7) input","extractor":{"type":"attribute","name":"value"}},
                                                                                                                    ]
                                                                                                  }
                                                                                   },
                                                              "url":"https://apple.kukkia.jp/bin/ovs_pi.php",
                                                              }
                                                           ]
                                            }
        test_kukkiapple_order_list_scraping =  {
                                                 "login":{"url":"https://apple.kukkia.jp/bin/login.php","login":{"name":"login_id","value":"kukkia"},"password":{"name":"login_pw","value":"kukkiapple"},"fields":[{"name":"bst","value":"1024"},{"name":"bsy","value":"1280"}]},
                                                 "scrap_list":[
                                                                 {
                                                                  "encoding":"utf-8",
                                                                  "fields":[{"name":"cmd","value":"list"},
                                                                            {"name":"stxt","value":""},
                                                                            {"name":"s_cus_id","value":""},
                                                                            {"name":"date_st","value":""},
                                                                            {"name":"date_en","value":""},
                                                                            {"name":"bst","value":"1024"},
                                                                            {"name":"bsy","value":"1280"}
                                                                            ],
                                                                  "selectors":{"edit_onclick":{"string":"div#ajax_area tr td:nth-child(8) a[onclick]","extractor":{"type":"attribute","name":"onclick"}},
                                                                               "order_id":{"string":"div#ajax_area tr td:nth-child(1)","extractor":{"type":"text"}}
                                                                               },
                                                                  "urls":["https://apple.kukkia.jp/bin/ovs_pi.php"]
                                                                  },
                                                        ]
                                                }
        s = WebsiteScraper()
        scraps = s.scrap(test_kukkiapple_order_list_scraping)
        logging.info(scraps)
        self.render_response('/pascra_request.html', **kwargs)

    def post(self,**kwargs):
        testdata = {"url":"http://www6.nhk.or.jp/kokusaihoudou/archive/archive.html?i=151106","encoding":"utf-8","selectors":["nav>ul>li>a"]}
        testdata = {"login":{"url":"https://apple.kukkia.jp/bin/login.php","login":{"name":"login_id","value":"kukkia"},"password":{"name":"login_pw","value":"kukkiapple"},"fields":[{"name":"bst","value":"1024"},{"name":"bsy","value":"1280"}]},
                    }
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
        #logging.info(response.read())
        self.response.write(response.read())

class ScrapingHandler(BaseHandler):
    def get(self,**kwargs):
        self.render_response('/pascra.html', **kwargs)
    def post(self,**kwargs):
        scraper = WebsiteScraper()
        scraps = scraper.scrap(self.request.get('json'))
        logging.info('response')
        logging.info(scraps)
        self.response.write(json.dumps(scraps))
        


config = {}

app = webapp2.WSGIApplication([
                               webapp2.Route(r'/scrap/page/request', RequestTestingHandler),
                               webapp2.Route(r'/scrap/page', ScrapingHandler),
                               ('.*', MiscHandler)
                              ],
                              config=config,
                              debug=False)
