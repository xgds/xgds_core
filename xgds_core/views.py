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
import traceback
import os
import glob
import json
import datetime
from django.utils import timezone

import couchdb

from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q

from django.template import loader
from django.conf import settings
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.template import RequestContext
from django.utils.translation import ugettext, ugettext_lazy as _
from django.core.cache import caches
from django.http import (HttpResponse,
                         HttpResponseNotAllowed)

from xgds_core.models import TimeZoneHistory
from geocamUtil.loader import LazyGetModelByName


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


def get_handlebar_as_string(request, handlebarPath):
    template_file = os.path.join(settings.PROJ_ROOT, 'apps', handlebarPath)
    with open(template_file, 'r') as infile:
        result = infile.read()
        return HttpResponse(result, content_type='text/plain', status=200)
    
    
def update_session(request, key, value):
    ''' Update session variable '''
    if not request.is_ajax() or not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    
    request.session[request.POST['key']] = request.POST['value']
    return HttpResponse(json.dumps({'Success':"True"}), content_type='application/json')


def set_cookie(response, key, value, days_expire = 7):
    if days_expire is None:
        max_age = 365 * 24 * 60 * 60  #one year
    else:
        max_age = days_expire * 24 * 60 * 60 
    expires = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=max_age), "%a, %d-%b-%Y %H:%M:%S GMT")
    response.set_cookie(key, value, max_age=max_age, expires=expires, domain=settings.SESSION_COOKIE_DOMAIN, secure=settings.SESSION_COOKIE_SECURE or None)

    
def update_cookie(request, key, value):
    ''' Update cookie variable '''
    if not request.is_ajax() or not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    
    response =  HttpResponse(json.dumps({'Success':"True"}), content_type='application/json')
    set_cookie(response, key, value)
    return response


def get_file_from_couch(docDir, docName):
    if docDir[-1] == '/':  #get rid of the trailing slash
        docDir = docDir[:len(docDir)-1]  
    docPath = "%s/%s" % (docDir, docName)
    dbServer = couchdb.Server()
    db = dbServer[settings.COUCHDB_FILESTORE_NAME]
    doc = db[docPath]
    # By convention, attachment has the same basename as document
    dataStream = db.get_attachment(doc, docName).read()
    return dataStream
    
    
def get_db_attachment(request, docDir, docName):
    docPath = "%s/%s" % (docDir, docName)
    dbServer = couchdb.Server()
    db = dbServer[settings.COUCHDB_FILESTORE_NAME]
    doc = db[docPath]
    # By convention, attachment has the same basename as document
    attDataStream = db.get_attachment(doc, docName)
    attData = attDataStream.read()
    attDataStream.close()
    attMimeType = doc["_attachments"][docName]["content_type"]
    
    response = HttpResponse(attData, content_type=attMimeType)
    return response


class OrderListJson(BaseDatatableView):
    """
    Ways to look up json for datatables for objects
    """
    
    model = None
    
    # dictionary that is for our filter
    filterDict = {}
    
    # to hold the Q queries for or-ing a search
    queries = None
    
    # set max limit of records returned, this is used to protect our site if someone tries to attack our site
    # and make it return huge amount of data
    max_display_length = 100
    
    def lookupModel(self, modelName):
        try:
            self.model = LazyGetModelByName(getattr(settings, modelName)).get()
        except:
            self.model = LazyGetModelByName(modelName).get()

    def dispatch(self, request, *args, **kwargs):
        if not self.model:
            if 'modelName' in kwargs:
                self.lookupModel(kwargs.get('modelName'))
        
        if 'filter' in kwargs:
            theFilter = kwargs.get('filter', None)
            self.buildFilterDict(theFilter)

        return super(OrderListJson, self).dispatch(request, *args, **kwargs)


    def addQuery(self, query):
        if self.queries:
            self.queries |= query
        else:
            self.queries = query
        
    def buildQuery(self, search):

        self.queries = None
        if search:
            try:
                for key in self.model.getSearchableFields():
                    self.addQuery(Q(**{key+'__icontains':search}))
                
                if unicode(search).isnumeric():
                    for key in self.model.getSearchableNumericFields():
                        self.addQuery(Q(**{key:search}))
            except:
                try:
                    self.model._meta.get_field('name')
                    self.addQuery(Q(**{'name__icontains':search}))
                except:
                    pass
                
                try:
                    self.model._meta.get_field('description')
                    self.addQuery(Q(**{'description__icontains':search}))
                except:
                    pass
        
    def buildFilterDict(self, theFilter):
        dictEntries = str(theFilter).split(",")
        for entry in dictEntries:
            splits = str(entry).split(":")
            try:
                value = int(splits[1]);
                self.filterDict[splits[0]] = value
            except:
                self.filterDict[splits[0]] = splits[1]

    def filter_queryset(self, qs):
        if self.filterDict:
            qs = qs.filter(**self.filterDict)
        
        todayOnly = self.request.GET.get(u'today', u'true')
        if todayOnly == u'true':
            timesearchField = self.model.timesearchField()
            if timesearchField != None:
                today = timezone.localtime(timezone.now()).date()
                filterDict = { timesearchField + '__gt': today}
                qs = qs.filter(**filterDict)
            
        # TODO handle search with sphinx
        search = self.request.GET.get(u'search[value]', None)
        if search:
            self.buildQuery(str(search))
            if self.queries:
                qs = qs.filter(self.queries)
        
        last = self.request.GET.get(u'last', -1)
        if last > 0:
            qs = qs[-last:]
        
        return qs