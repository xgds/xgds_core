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

import json
import datetime
from dateutil.parser import parse as dateparser

from xgds_core.util import callUrl
from geocamUtil.datetimeJsonEncoder import DatetimeJsonEncoder


from django.conf import settings
from django.http import JsonResponse

if settings.XGDS_CORE_REDIS:
    import redis
    rs = redis.Redis(host='localhost', port=settings.XGDS_CORE_REDIS_PORT)

    def queueRedisData(channel, jsonString):
        rs.lpush(channel, jsonString)
        
    def publishRedisSSE(channel, sse_type, jsonString):
        message_string = json.dumps({"type":sse_type, "data": jsonString})
        rs.publish(channel, message_string)
        
    def publishRedisSSEAtTime(channel, sse_type, jsonString, publishTime):
        publish_info = {"channel": channel,
                        "publishTime": publishTime.isoformat(),
                        "messageString": {"type":sse_type, "data": jsonString}}
        rebroadcastString = json.dumps(publish_info)
        rs.rpush(settings.XGDS_CORE_REDIS_REBROADCAST, rebroadcastString)
        
    def getSseActiveChannels(request):
        # Look up the active channels we are using for SSE
        return JsonResponse(settings.XGDS_SSE_CHANNELS, safe=False)
    


def callRemoteRebroadcast(channel, sseType, jsonString, eventTime=None):
    if not eventTime:
        eventTime = datetime.datetime.utcnow()

    ''' Rebroadcast this information on the remote machines that are registered in settings.py for a delayed sse event'''
    data = {"channel":channel,
            "sseType":sseType,
            "jsonString": jsonString,
            "eventTime": eventTime.isoformat()}
    
    urlSuffix = '/xgds_core/rest/rebroadcast/sse/'
    username = settings.XGDS_CORE_SSE_REMOTE_USERNAME
    password = settings.XGDS_CORE_SSE_REMOTE_TOKEN
    
    for remoteSite in settings.XGDS_CORE_SSE_REBROADCAST_SITES:
        url = remoteSite + urlSuffix
        result  = callUrl(url, username, password, 'POST', data, True)
