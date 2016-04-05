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
import glob

from django.conf import settings
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.template import RequestContext
from django.utils.translation import ugettext, ugettext_lazy as _
from django.core.cache import caches

from xgds_core.models import TimeZoneHistory


def getTimeZone(inputTime):
    ''' For a given time, look in the TimeZoneHistory to see what the time zone was set to at that time.
    '''
    result = TimeZoneHistory.objects.filter(startTime__lte=inputTime, endTime__gte=inputTime)
    if result.count() > 0:
        return result[0].timeZone
    else:
        return settings.TIME_ZONE


def get_handlebars_templates(source, key):
    _template_cache = caches['default']
    templates = None
    if key in _template_cache:
        templates = _template_cache.get(key)
    if settings.XGDS_CORE_TEMPLATE_DEBUG or not templates:
        templates = {}
        for thePath in source:
            inp = os.path.join(settings.PROJ_ROOT, 'apps', thePath)
            for template_file in glob.glob(os.path.join(inp, '*.handlebars')):
                with open(template_file, 'r') as infile:
                    template_name = os.path.splitext(os.path.basename(template_file))[0]
                    templates[template_name] = infile.read()
        _template_cache.set(key, templates)
    return templates