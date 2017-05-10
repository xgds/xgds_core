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

"""
This app may define some new parameters that can be modified in the
Django settings module.  Let's say one such parameter is FOO.  The
default value for FOO is defined in this file, like this:

  FOO = 'my default value'

If the admin for the site doesn't like the default value, they can
override it in the site-level settings module, like this:

  FOO = 'a better value'

Other modules can access the value of FOO like this:

  from django.conf import settings
  print settings.FOO

Don't try to get the value of FOO from django.conf.settings.  That
settings object will not know about the default value!
"""
from geocamUtil.SettingsUtil import getOrCreateArray, getOrCreateDict

XGDS_CORE_TEMPLATE_DEBUG = False # If this is true, handlebars templates will not be cached.
XGDS_CORE_TEMPLATE_DIRS = getOrCreateDict('XGDS_CORE_TEMPLATE_DIRS')  # a dictionary to store directories of handlebars to load based on class name
XGDS_CORE_LIVE_INDEX_URL = '/'

#support for data relay via REDIS
XGDS_CORE_RELAY_SUBDIRECTORY = 'relay/'
XGDS_CORE_REDIS = False
XGDS_CORE_REDIS_PORT = 6379
XGDS_CORE_REDIS_RELAY_CHANNEL = 'dataRelayQueue'
XGDS_CORE_REDIS_RELAY_ACTIVE = 'dataRelayActive'

# override to include SSE; right now we are based on flask-sse nginx and redis
XGDS_SSE = False
# extend this if you have your own channels, for example one per vehicle
XGDS_SSE_CHANNELS = ['sse']

XGDS_CORE_CONDITION_MODEL = "xgds_core.Condition"
XGDS_CORE_CONDITION_HISTORY_MODEL = "xgds_core.ConditionHistory"

BOWER_INSTALLED_APPS = getOrCreateArray('BOWER_INSTALLED_APPS')
BOWER_INSTALLED_APPS += ['moment',
                         'moment-timezone',
                         'moment-duration-format',
                         'moment-range#2.1.0',
                         'gridstack#0.2.6']

FILE_UPLOAD_PERMISSIONS = 0o644
