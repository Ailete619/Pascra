# -*- coding: utf-8 -*-
'''

@author: ailete
'''
from google.appengine.ext import ndb
import logging

class DataRequest(ndb.Model):
    referer = ndb.StringProperty()
    @classmethod
    def validate(cls,edr_id,referer,edr_eof="False"):
        logging.info(cls.__name__+".validate("+str(edr_id)+","+referer+","+str(edr_eof)+")")
        edr_key = ndb.Key(urlsafe=edr_id)
        external_data_request = edr_key.get()
        if not external_data_request:
            logging.warning(cls.__name__+".validate("+str(edr_id)+", "+referer+") : unknown request id '"+str(edr_id)+"'!")
            return False
        if not external_data_request.referer == referer:
            #logging.info(external_data_request.referer)
            logging.warning(cls.__name__+".validate("+str(edr_id)+", "+referer+") : unknown referer '"+referer+"'!")
            return False
        logging.info("edr_eof="+str(edr_eof))
        if edr_eof == "True":
            external_data_request.key.delete()
        return True
    