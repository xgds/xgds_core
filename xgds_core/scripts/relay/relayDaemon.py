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
import pydevd
import redis
import json
import requests
import traceback
import datetime
import logging

import django
django.setup()

from django.conf import settings
from xgds_core.models import RelayEvent, RelayFile

rs = redis.Redis(host='localhost', port=settings.XGDS_CORE_REDIS_PORT)

def relayListener(opts):
    # callback from Redis to handle stored data and files that are waiting to be relayed
    logging.info('RELAY LISTENER RUNNING')
    pydevd.settrace('192.168.0.11')
    while True:
        # see if we had already active relays
        active = rs.rpop(settings.XGDS_CORE_REDIS_RELAY_ACTIVE)
        while active:
            # handle previously active event
            relayData(active, opts)
            # get next one
            active = rs.rpop(settings.XGDS_CORE_REDIS_RELAY_ACTIVE)
    
        # handle newly broadcast data to relay
        active = rs.brpoplpush(settings.XGDS_CORE_REDIS_RELAY_CHANNEL, settings.XGDS_CORE_REDIS_RELAY_ACTIVE)
        relayData(active, opts)
    
    
def relayData(active, opts):
    # actually do the relaying to the remote host
    pydevd.settrace('192.168.0.11')
    try:
        event = RelayEvent.objects.get(pk=json.loads(active).relay_event_pk)
        logging.info('RELAY BEGIN %d' % event.pk)
        url = "%s/%s" % (opts.namedHost, event.url)
        files = {}
        for f in event.relayfile_set.all():
            files[f.file_key] = f.file_to_send
        #TODO handle pk matching
        response = requests.post(url, json=event.serialized_form, files=files, timeout=opts.timeout)
        if response.status_code == requests.codes.ok:
            event.relay_success_time = datetime.datetime.utcnow()
            rs.rpop(settings.XGDS_CORE_REDIS_RELAY_ACTIVE)
            logging.info('RELAY SUCCESS %d' % event.pk)
        else:
            logging.warning('RELAY FAIL %d. Status Code: %d' % (event.pk, response.status_code))
            
    except:
        logging.warning('ERROR IN RELAY DATA')
        traceback.print_exc()


def main():
    import optparse
    parser = optparse.OptionParser('usage: %prog')
    parser.add_option('-t', '--timeout',
                      default=30,
                      help='Timeout in seconds for response from HTTP relay post.')
    parser.add_option('-n', '--namedHost',
                      help='Name of remote host to relay to, ie http://shore.xgds.org')
    opts, args = parser.parse_args()
    if args:
        parser.error('expected no args')
    logging.basicConfig(level=logging.DEBUG)


if __name__ == '__main__':
    main()