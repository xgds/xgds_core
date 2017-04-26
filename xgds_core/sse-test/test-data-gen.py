#! /usr/bin/env python

import time
from redis import StrictRedis
from flask_sse import Message
import json

count = 0
redis=StrictRedis.from_url("redis://localhost")

print "Sending SSE events..."

while True:
    msgBody = {"message":"I can count to %s" % count}
    messageObj = Message(msgBody, type='greeting')
    msg_json = json.dumps(messageObj.to_dict())
    subCount = redis.publish(channel='sse', message=msg_json)
    count += 1
    time.sleep(0.25)
