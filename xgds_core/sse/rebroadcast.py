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

import logging
import time
from dateutil.parser import parse as dateparser

import redis
import json
import traceback
import datetime

import django
from numpy import broadcast
django.setup()

from django.conf import settings

from geocamUtil.datetimeJsonEncoder import DatetimeJsonEncoder
rs = redis.Redis()

'''
Rebroadcast blocks until it gets something on the redis rebroadcast queue.
Then it waits if need be until the right time to broadcast
Then it pushes it out on the sse queue.
IF we are ever getting data in non sequential time order this could block this whole process.
We are not expecting that now.
'''
def main():
    logging.warning('*** starting up ***')
    while True:
        #logging.warning('**** ABOUT TO BLOCK FOR NEXT THINGY ****')
        channel, next = rs.blpop(settings.XGDS_CORE_REDIS_REBROADCAST)
        #logging.warning('***** NEW THINGY *****')
        nextDict = json.loads(next)
        publishTime = dateparser(nextDict['publishTime'])
        now = datetime.datetime.utcnow()
        
        if publishTime > now:
            delta = publishTime - now
            deltaSeconds = delta.seconds
            #logging.warning('SLEEPING FOR SECONDS %d' % deltaSeconds)
            time.sleep(deltaSeconds)
        
        channel = nextDict['channel']
        messageString = nextDict['messageString']
        # publish to the right sse queue
        #logging.warning('PUBLISHING CHANNEL: %s ' % channel)
        rs.publish(channel, json.dumps(messageString, cls=DatetimeJsonEncoder))
        #logging.warning('DONE PUBLISHING')
            

if __name__ == '__main__':
    main()
