#!/usr/bin/env python3

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

#
# Really clunky test program to test redis/tornado SSE setup
# Publishes lists of 100 random words from /usr/share/dict (see e.g. https://lists.ubuntu.com/archives/ubuntu-users/2005-July/043882.html)
# and a title line on the redis channel "testp" (under SSE types/events wordsalad and titletext respectively) Also publishes a 
# running counter on the redis "testsse" channel with SSE type/event "thecount"
#

import random
import redis
import time, datetime
import json
from uuid import uuid4

wf = open("/usr/share/dict/words","r", encoding="utf-8")
wl = [line.strip() for line in wf.readlines()]

rs = redis.StrictRedis(host="redis")

print("Starting publisher")
prevcount = -1
prevother = -1
titlePhase = 0
counter = 1
while True:
    wordList = random.sample(wl,100)
    wordString = " ".join(wordList)
    wordDict = {"data":wordString, "type":"wordsalad", "id":str(uuid4()), "retry":1500}
    rs.publish("testp", json.dumps(wordDict))
    if titlePhase == 0:
        titleDict = {"data":"Title Foo", "type":"titletext", "id":str(uuid4()), "retry":1500}
        rs.publish("testp", json.dumps(titleDict))
    elif titlePhase == 2:
        titleDict = {"data":"Title Bar", "type":"titletext", "id":str(uuid4()), "retry":1500}
        rs.publish("testp", json.dumps(titleDict))
    titlePhase = (titlePhase + 1) % 4
    otherDict = {"data":"I can count to: " + str(counter), "type":"thecount", "id":counter, "retry":1500}
    rs.publish("testsse", json.dumps(otherDict))
    counter += 1
    ch1, newcount, ch2, otherCount = rs.execute_command("PUBSUB", "NUMSUB", "testp", "testsse")
    if newcount != prevcount or prevother != otherCount:
        timestamp = datetime.datetime.now().isoformat()
        print("{}: Subscriber count: {}/{}".format(timestamp, newcount, otherCount))
        prevcount = newcount
        prevother = otherCount
    time.sleep(2)
