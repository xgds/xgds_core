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
import redis
import json
import requests
import logging
import urlparse
from requests.adapters import HTTPAdapter

import django
django.setup()

from django.conf import settings

rs = redis.Redis(host='localhost', port=settings.XGDS_CORE_REDIS_PORT)
nicknames = []
auth = {}

sessions = {}

TIMEOUT = 15
MAX_RETRIES = 3 # HTTP REQUEST RETRIES
SLEEP_TIME = 5.0
MAX_SEND_ATTEMPTS = 3


def getSession(url):
    parsed = urlparse.urlparse(url)
    key = parsed.scheme + '//' + parsed.netloc
    
    if key not in sessions:
        s = requests.Session()
        s.mount(key, HTTPAdapter(max_retries=MAX_RETRIES))
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
        return s.post(config['url'], data=config['data'], timeout=TIMEOUT)
    elif config['method'] == 'GET':
        return s.get(config['url'], timeout=TIMEOUT)


def handleQueue():
    logging.warning('*** starting up ***')
    while True:
        logging.warning('**** ABOUT TO BLOCK FOR NEXT URL ****')
        channel, next = rs.brpop(settings.XGDS_CORE_REDIS_SESSION_MANAGER)
        config = json.loads(next)
        counter = 0
        while True and counter < MAX_SEND_ATTEMPTS:
            try:
                counter += 1
                if counter == MAX_SEND_ATTEMPTS:
                    print 'LAST ATTEMPT'
                callUrl(config)
                break
            except:
                # wait for SLEEP_TIME seconds and try the same active item again
                print 'HIT EXCEPTION, retrying ...'
                time.sleep(SLEEP_TIME)
        


def main():
    handleQueue()


if __name__ == '__main__':
    main()
