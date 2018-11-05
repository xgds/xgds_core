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

import os
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.conf import settings
import urlparse
import json
import requests
if settings.XGDS_CORE_REDIS:
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
    if shareSession and settings.XGDS_CORE_REDIS:
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
    """ Insert a string after the first block in a path, for example
    /my/original/path,insertion
    /my/INSERTION/original/path
    """
    slashIndex = original.index('/',1)
    newString = '%s/%s%s' % (original[0:slashIndex], insertion, original[slashIndex:len(original)])
    return newString


def get_all_subclasses(the_class, check_meta_abstract=True, top=True):
    """
    Returns all the subclasses of the given class
    :param the_class: parent class
    :param check_meta_abstract: False to not check the abstract setting on a django model
    :param top: true if this is the 'top call', ie non recursive call
    :return: set of all subclasses
    """
    kids = the_class.__subclasses__()

    result = set(kids).union(
            [s for c in kids for s in get_all_subclasses(c, check_meta_abstract, False)])

    if top:
        if check_meta_abstract:
            non_abstract_result = []
            for k in result:
                if not k._meta.abstract:
                    non_abstract_result.append(k)
            result = non_abstract_result
    return result


def build_relative_path(full_path, prefix='/', split_on='/data/'):
    """
    Given a full file path on the hard drive return a relative path to the data directory
    ie /full/path/to/data/my/file
    :param full_path:  The original full path to a file
    :param prefix: The prefix of the result
    :param split_on: The string in the path to split on, included in the result.
    :return: the relative path, ie '/data/my/file
    """
    splits = full_path.split(split_on)
    return os.path.join(prefix, split_on, splits[-1])
