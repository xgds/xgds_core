#!/usr/bin/env python
# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
#
# The xGDS platform is licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
# __END_LICENSE__
import time
import pytz
import redis
import json
import requests
import traceback
import datetime
import logging
import urlparse
import threading

import django
#from __builtin__ import None
django.setup()

from django.conf import settings

rs = redis.Redis(host='localhost', port=settings.XGDS_CORE_REDIS_PORT)
nicknames = []
hostlist = None
auth = {}

sessions = {}

def getSession(url):
    #url = config['url']
    parsed = urlparse.urlparse(url)
    key = parsed.scheme + '//' + parsed.netloc
    
    if key not in sessions:
        s = requests.Session()
        sessions[key] = s
    
    logging.warning('session count: %d' % len(sessions))
    return sessions[key]


def callUrl(config):
    logging.warning('CALLING URL %s' % config['url'])
    s = getSession(config['url'])   
    logging.warning(str(s))
    if config['username']:
        s.auth = (config['username'], config['password'])
    if config['method'] == 'POST':
        return s.post(config['url'], data=config['data'])
    elif config['method'] == 'GET':
        return s.get(config['url']) 

def handleQueue():
    logging.warning('*** starting up ***')
    while True:
        logging.warning('**** ABOUT TO BLOCK FOR NEXT URL ****')
        channel, next = rs.brpop(settings.XGDS_CORE_REDIS_SESSION_MANAGER)
        config = json.loads(next)
        callUrl(config)

def main():
    handleQueue()

if __name__ == '__main__':
    main()
