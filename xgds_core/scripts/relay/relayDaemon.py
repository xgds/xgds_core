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
import redis
import json
import requests
import traceback
import datetime
import logging
import threading
from urlparse import urlparse

import django
django.setup()

from django.conf import settings
from xgds_core.models import RelayEvent, RelayFile

rs = redis.Redis(host='localhost', port=settings.XGDS_CORE_REDIS_PORT)
nicknames = []
hostlist = None

def runRelayListeners(timeout):
    threads = []
    for index, hosturl in enumerate(hostlist):
        #logging.info('BUILDING THREAD FOR ' + hosturl)
        print 'BUILDING THREAD FOR ' + hosturl
        relayThread = threading.Thread(target=relayListener, name=hosturl, args=(timeout, hosturl, nicknames[index]))
        threads.append(relayThread)
        relayThread.start()
    return threads

def propagateRelaysToHosts():
#     logging.info('PROPAGATING RELAYS TO HOST CHANNELS')
    print 'PROPAGATING RELAYS TO HOST CHANNELS'
    while True:
        latest_relay = rs.lrange(settings.XGDS_CORE_REDIS_RELAY_CHANNEL, -1, -1)
        while latest_relay:
            print str(latest_relay)
#             logging.info(str(latest_relay))
            for nickname in nicknames:
                print 'sending thing to ' + settings.XGDS_CORE_REDIS_RELAY_CHANNEL + '_'+ nickname
                rs.lpush(settings.XGDS_CORE_REDIS_RELAY_CHANNEL + '_' + nickname, latest_relay[1])
            latest_relay = rs.lrange(settings.XGDS_CORE_REDIS_RELAY_CHANNEL, -1, -1)
        
        latest_relay = rs.brpop(settings.XGDS_CORE_REDIS_RELAY_CHANNEL)
#         logging.info(str(latest_relay))
        print str(latest_relay)
        for nickname in nicknames:
            print 'sending thing to ' + settings.XGDS_CORE_REDIS_RELAY_CHANNEL + '_'+ nickname
            rs.lpush(settings.XGDS_CORE_REDIS_RELAY_CHANNEL + '_' + nickname, latest_relay[1])
        
    
def relayListener(timeout, hosturl, nickname):
    # callback from Redis to handle stored data and files that are waiting to be relayed
#     logging.info('RELAY LISTENER RUNNING FOR ' + hosturl)
    print 'RELAY LISTENER RUNNING FOR ' + hosturl
    
    while True:
        # see if we had already active relays
        active = rs.lrange(settings.XGDS_CORE_REDIS_RELAY_ACTIVE + '_' + nickname, -1, -1)
        while active:
            # handle previously active event
            relayData(active[0], timeout, hosturl, nickname)

            # get next one
            active = rs.lrange(settings.XGDS_CORE_REDIS_RELAY_ACTIVE + '_' + nickname, -1, -1)
    
        # handle newly broadcast data to relay
        active = rs.brpoplpush(settings.XGDS_CORE_REDIS_RELAY_CHANNEL + '_' + nickname, settings.XGDS_CORE_REDIS_RELAY_ACTIVE + '_' + nickname)
#         logging.info('just got an active thing for ' + nickname)
#         logging.info(active)
        print 'just got an active thing for ' + nickname
        print active
        relayData(active, timeout, hosturl, nickname)
    
    
def relayData(active, timeout, hosturl, nickname):
    # actually do the relaying to the remote host
    try:
        event = RelayEvent.objects.get(pk=json.loads(active)['relay_event_pk'])
#         logging.info('RELAY BEGIN %d' % event.pk)
        print 'RELAY BEGIN %d' % event.pk
        url = "%s%s" % (hosturl, '/xgds_core/relay/')
        files = {}
        for f in event.relayfile_set.all():
            files[f.file_key] = f.file_to_send
        #TODO handle pk matching and check for the pk and type somehow
        response = requests.post(url, data=event.getSerializedData(), files=files, timeout=timeout)
        if response.status_code == requests.codes.ok:
            event.relay_success_time = datetime.datetime.utcnow()
            event.save()
            rs.rpop(settings.XGDS_CORE_REDIS_RELAY_ACTIVE + '_' + nickname)
            print 'RELAY SUCCESS %d' % event.pk
#             logging.info('RELAY SUCCESS %d' % event.pk)
        else:
            logging.warning('RELAY FAIL %d. Status Code: %d' % (event.pk, response.status_code))
            
    except:
        logging.warning('ERROR IN RELAY DATA')
        traceback.print_exc()


def main():
    import optparse
    parser = optparse.OptionParser('usage: %prog hosturls')
    parser.add_option('-t', '--timeout',
                      default=30,
                      help='Timeout in seconds for response from HTTP relay post.')
    opts, args = parser.parse_args()
    if not args:
        parser.error('expected hosturl as argument (http://shore.xgds.org for example)')
    logging.basicConfig(level=logging.DEBUG)

    global hostlist
    hostlist = args[0].split(',')
    for hosturl in hostlist:
        netloc = urlparse(hosturl).netloc
        nicknames.append(netloc.split(':')[0])

    runRelayListeners(opts.timeout)
    propagateRelaysToHosts()
    

if __name__ == '__main__':
    main()
