#! /usr/bin/env python

import time
import pytz
import datetime
from redis import StrictRedis
from flask_sse import Message
import json

count = 0
redis=StrictRedis.from_url("redis://localhost")

while True:
    msgBody = {"count": count,
               'timestamp': datetime.datetime.now(pytz.utc).isoformat()}
    messageObj = Message(msgBody, type='heartbeat')
    msg_json = json.dumps(messageObj.to_dict())
    subCount = redis.publish(channel='sse', message=msg_json)
    count += 1
    time.sleep(5)
