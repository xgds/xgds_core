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
import traceback
import django
#from __builtin__ import None
django.setup()

from django.conf import settings
rs = redis.Redis()
queuename = None

def killEvent(pk):
    try:
        value = '{"relay_event_pk": ' + pk + '}'
        rs.lrem(queuename, value)
        print 'removed %s' % pk
    except:
        traceback.print_exc()
    
def listEvents():
    ''' list the events in the active redis queue for the given host'''
    print 'LEN: %d' % rs.llen(queuename)
    for i in rs.lrange(queuename, 0, -1):
        print i
    
def main():
    import optparse
    parser = optparse.OptionParser('usage: %prog dest')
    parser.add_option('-d', '--dest', default='boat.xgds.org', help='where the relay is pushing to')
    parser.add_option('-e', '--eventPK', default=None, help='PK of event to delete')
    
    opts, args = parser.parse_args()
    
    global queuename
    queuename = settings.XGDS_CORE_REDIS_RELAY_ACTIVE + '_' + opts.dest
    
    listEvents()
    
    if opts.eventPK:
        print 'DELETING ' + opts.eventPK
        killEvent(opts.eventPK)
        listEvents()
    
if __name__ == '__main__':
    main()
