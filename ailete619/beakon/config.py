# -*- coding: utf-8 -*-
'''

@author: Loic LE TEXIER
'''
import logging
import os  
import yaml

with open("beakon.yaml", "r") as f:
    settings = yaml.load(f)

locale = {}
for filename in os.listdir('locales'):
    if os.path.isfile("locales/"+filename):
        locale[filename[0:2]] = yaml.load(open("locales/"+filename, "r"))
