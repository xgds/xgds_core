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

from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.conf import settings
import urlparse
import json
import requests
from redisUtil import queueRedisData
from geocamUtil.datetimeJsonEncoder import DatetimeJsonEncoder

def get100Years():
    theNow = timezone.now() + relativedelta(years=100)
    return theNow

def addPort(url, port, http=True):
    ''' Add a port to a url '''
    if port:
        parsed = urlparse.urlparse(url)
        replaced = parsed._replace(netloc="{}:{}".format(parsed.hostname, port))
        if http:
            replaced = replaced._replace(scheme='http')
        return replaced.geturl()
    return url


def callUrl(url, username, password, method='GET', data=None, shareSession=False):
    ''' WARNING If you are calling this a lot of times then you will be opening a new connection and instead it should
    be run outside with a  pycroraptor service.'''
    if shareSession:
        # POST THIS ON SHARED SESSION FOR REDIS
        config = {'url':url,
                 'username': username,
                 'password': password,
                 'method': method,
                 'data': data}
        queueRedisData(settings.XGDS_CORE_REDIS_SESSION_MANAGER, json.dumps(config, cls=DatetimeJsonEncoder))
        return
    else:
        s = requests.Session()
    if username:
        s.auth = (username, password)
    if method == 'POST':
        return s.post(url, data=data)
    elif method == 'GET':
        return s.get(url)

    
def deletePostKey(post, theKey):
    try:
        if theKey in post:
            mutable = post._mutable
            post._mutable = True
            del post[theKey]
            post._mutable = mutable
    except:
        pass
    return post

def insertIntoPath(original, insertion='rest'):
    ''' Insert a string after the first block in a path, for example
    /my/original/path,insertion
    /my/INSERTION/original/path
    '''
    slashIndex = original.index('/',1)
    newString = '%s/%s%s' % (original[0:slashIndex], insertion, original[slashIndex:len(original)])
    return newString


