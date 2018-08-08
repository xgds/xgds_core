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
XGDS_CORE_RELAY = False  # IMPORTANT: set to true if you need relay
XGDS_CORE_RELAY_SUBDIRECTORY = 'relay/'
XGDS_CORE_REDIS_PORT = 6379
XGDS_CORE_REDIS = False
XGDS_CORE_REDIS_RELAY_CHANNEL = 'dataRelayQueue'
XGDS_CORE_REDIS_RELAY_ACTIVE = 'dataRelayActive'
XGDS_CORE_REDIS_REBROADCAST = 'sseRebroadcast'
XGDS_CORE_REDIS_SESSION_MANAGER = 'sessionManager'

# override to include SSE; right now we are based on flask-sse nginx and redis
XGDS_SSE = False
# extend this if you have your own channels, for example one per vehicle
XGDS_SSE_CHANNELS = ['sse']

XGDS_CORE_CONDITION_MODEL = "xgds_core.Condition"
XGDS_CORE_CONDITION_HISTORY_MODEL = "xgds_core.ConditionHistory"

COUCHDB_URL = "http://localhost:5984"

FILE_UPLOAD_PERMISSIONS = 0o644

# Extend this map to hold tablename to class mappings for those classes that support rebroadcast after tungsten replication
# for example, past position, current position, condition
XGDS_CORE_REBROADCAST_MAP = getOrCreateDict('XGDS_CORE_REBROADCAST_MAP')
XGDS_CORE_REBROADCAST_MAP.update({'xgds_core_conditionhistory':{'modelName':'xgds_core.ConditionHistory', 'pkColNum':1, 'pkType': 'int'}})
                                  #'geocamTrack_linestyle': {'modelName':'geocamTrack.LineStyle', 'pkColNum':1, 'pkType': 'int'}})

# For sse rebroadcast on remote machines, set this up in settings.py
XGDS_CORE_SSE_REBROADCAST_SITES = []
XGDS_CORE_SSE_REMOTE_USERNAME = ''
XGDS_CORE_SSE_REMOTE_TOKEN = ''

# TODO override this for the channels you will broadcast conditions on
XGDS_SSE_CONDITION_CHANNELS = ['sse']

# Settings for running Open Web Analytics
INCLUDE_OWA_TRACKING = False
OWA_SITE_URL = ""
OWA_SITE_ID = ""

# Add mappings from a dropdown to an import page from the import landing page.
XGDS_DATA_IMPORTS = {}


# Add mappings to the importer for csv importers defined by yaml files
XGDS_CORE_CSV_IMPORTER = {}

# Override this to provide a function that will return a dictionary of current state information.
# This will be appended to items as they are imported.
XGDS_CORE_CURRENT_STATE_FUNCTION = 'xgds_core.util.getCurrentStateDictionary'

XGDS_CORE_FLIGHT_MODEL = "xgds_core.Flight"
XGDS_CORE_ACTIVE_FLIGHT_MODEL = "xgds_core.ActiveFlight"
XGDS_CORE_GROUP_FLIGHT_MODEL = "xgds_core.GroupFlight"
XGDS_CORE_VEHICLE_MODEL = 'xgds_core.Vehicle'
XGDS_CORE_VEHICLE_MONIKER = 'Vehicle'
XGDS_CORE_FLIGHT_MONIKER = "Flight"
XGDS_CORE_GROUP_FLIGHT_MONIKER = "Group Flight"
XGDS_CORE_DEFAULT_VEHICLE_PK = 1  # To be used when vehicle is required but not specified.

XGDS_CORE_SHOW_FLIGHT_MANAGEMENT = True
XGDS_CORE_ADD_GROUP_FLIGHT = True


# to be used by forms
XGDS_CORE_DATE_FORMATS = [
    '%m-%d-%y %H:%M:%S',
    '%m-%d-%y %H:%M:%S.%f', 
    '%m-%d-%y %H:%M', 
    '%m-%d-%y', 
    '%m/%d/%y %H:%M:%S',
    '%m/%d/%y %H:%M:%S.%f',
    '%m-%d-%y %H:%M:%S 00:00',
    '%m-%d-%y %H:%M:%S.%f 00:00',
    '%m-%d-%y %H:%M:%S.%f+00:00',
    '%m/%d/%y %H:%M:%S UTC',
    '%m/%d/%y %H:%M:%S.%f UTC',
    '%m-%d-%y %H:%M:%S UTC',
    '%m-%d-%y %H:%M:%S.%f UTC',
    '%m-%d-%yT%H:%M:%S+00:00',
    '%m-%d-%yT%H:%M:%S.%f+00:00',
    '%m-%d-%yT%H:%M:%S 00:00',
    '%m-%d-%yT%H:%M:%S.%f 00:00',
    '%m-%d-%yT%H:%M:%SZ',
    '%m-%d-%yT%H:%M:%S.%fZ',
    
    '%m-%d-%Y %H:%M:%S',
    '%m-%d-%Y %H:%M:%S.%f', 
    '%m-%d-%Y %H:%M', 
    '%m-%d-%Y', 
    '%m/%d/%Y %H:%M:%S',
    '%m/%d/%Y %H:%M:%S.%f',
    '%m-%d-%Y %H:%M:%S 00:00',
    '%m-%d-%Y %H:%M:%S.%f 00:00',
    '%m-%d-%Y %H:%M:%S.%f+00:00',
    '%m/%d/%Y %H:%M:%S UTC',
    '%m/%d/%Y %H:%M:%S.%f UTC',
    '%m-%d-%Y %H:%M:%S UTC',
    '%m-%d-%Y %H:%M:%S.%f UTC',
    '%m-%d-%YT%H:%M:%S+00:00',
    '%m-%d-%YT%H:%M:%S.%f+00:00',
    '%m-%d-%YT%H:%M:%S 00:00',
    '%m-%d-%YT%H:%M:%S.%f 00:00',
    '%m-%d-%YT%H:%M:%SZ',
    '%m-%d-%YT%H:%M:%S.%fZ',
    
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S.%f', 
    '%Y-%m-%d %H:%M', 
    '%Y-%m-%d', 
    '%Y/%m/%d %H:%M:%S',
    '%Y/%m/%d %H:%M:%S.%f',
    '%Y-%m-%d %H:%M:%S 00:00',
    '%Y-%m-%d %H:%M:%S.%f 00:00',
    '%Y-%m-%d %H:%M:%S.%f+00:00',
    '%Y/%m/%d %H:%M:%S UTC',
    '%Y/%m/%d %H:%M:%S.%f UTC',
    '%Y-%m-%d %H:%M:%S UTC',
    '%Y-%m-%d %H:%M:%S.%f UTC',
    '%Y-%m-%dT%H:%M:%S+00:00',
    '%Y-%m-%dT%H:%M:%S.%f+00:00',
    '%Y-%m-%dT%H:%M:%S 00:00',
    '%Y-%m-%dT%H:%M:%S.%f 00:00',
    '%Y-%m-%dT%H:%M:%SZ',
    '%Y-%m-%dT%H:%M:%S.%fZ',
]
