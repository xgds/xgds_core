#! /usr/bin/env python

import time
import pytz
import datetime
from redis import StrictRedis
import json

import django
django.setup()

from django.conf import settings
from xgds_core.redisUtil import publishRedisSSE

count = 0

while True:
    msgBody = {"count": count,
               'timestamp': datetime.datetime.now(pytz.utc).isoformat()}
    msg_json = json.dumps(msgBody)
    dontSkip = (count % 4 == 0)
    for channel in settings.XGDS_SSE_CHANNELS:
        if channel == 'sse' or dontSkip:
            publishRedisSSE(channel, 'heartbeat', msg_json)
    count += 1
    time.sleep(10)
