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
import pytz
import glob
import json
import datetime
import httplib
import threading
from dateutil.parser import parse as dateparser

from django.utils import timezone
from django.http import Http404

import couchdb

from django.core.serializers import serialize
from django.forms.models import model_to_dict
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import resolve

from django_datatables_view.base_datatable_view import BaseDatatableView
from django.views.decorators.cache import never_cache
from django.db.models import Q

from django.views.decorators.cache import cache_page
from django.template import loader
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404, JsonResponse
from django.template import RequestContext
from django.utils.translation import ugettext, ugettext_lazy as _
from django.core.cache import caches
from django.http import (HttpResponse,
                         HttpResponseNotAllowed)

from geocamUtil.loader import LazyGetModelByName

from xgds_core.models import TimeZoneHistory, DbServerInfo, Constant, RelayEvent, RelayFile
from apps.geocamUtil.datetimeJsonEncoder import DatetimeJsonEncoder

if settings.XGDS_CORE_REDIS:
    from xgds_core.redisUtil import queueRedisData
    from xgds_core.redisUtil import publishRedisSSE


def buildFilterDict(theFilter):
    if isinstance(theFilter, dict):
        return theFilter
    filterDict = {}
    dictEntries = str(theFilter).split(",")
    for entry in dictEntries:
        splits = str(entry).split(":")
        try:
            value = int(splits[1]);
            filterDict[splits[0]] = value
        except:
            filterDict[splits[0]] = splits[1]
    return filterDict

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
    
    
@cache_page(60 * 15)
def get_db_attachment(request, docDir, docName):
    try:
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
    except:
        raise Http404("CouchDB Object does not exist for: %s/%s" % (docDir, docName))


class OrderListJson(BaseDatatableView):
    """
    Ways to look up json for datatables for objects
    """
    
    model = None
    
    # dictionary that is for our filter
    filterDict = {}
    
    # to hold the Q queries for or-ing a search
    queries = None
    
    # to hold the anded Q queries from the form
    formQueries = None
    
    # set max limit of records returned, this is used to protect our site if someone tries to attack our site
    # and make it return huge amount of data
    max_display_length = 100
    
    def lookupModel(self, modelName):
        try:
            self.model = LazyGetModelByName(getattr(settings, modelName)).get()
        except:
            self.model = LazyGetModelByName(modelName).get()

    @never_cache
    def dispatch(self, request, *args, **kwargs):
        self.filterDict.clear()

        if not self.model:
            if 'modelName' in kwargs:
                self.lookupModel(kwargs.get('modelName'))
        
        if self.form:
            filledForm = self.form(request.POST)
            if filledForm.is_valid():
                self.formQueries = filledForm.getQueries()
            else:
                print 'invalid form'
                print str(filledForm.errors)

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
            splits = str(entry).split("|")
            try:
                value = int(splits[1]);
                self.filterDict[splits[0]] = value
            except:
                self.filterDict[splits[0]] = splits[1]

    def filter_queryset(self, qs):
        if self.formQueries:
            qs = qs.filter(self.formQueries)
        elif self.filterDict:
            qs = qs.filter(**self.filterDict)
        
        defaultToday = u'true' if settings.GEOCAM_UTIL_LIVE_MODE else  u'false'
        todayOnly = self.request.POST.get(u'today', defaultToday)
        if todayOnly == u'true':
            timesearchField = self.model.timesearchField()
            if timesearchField != None:
                today = timezone.localtime(timezone.now()).date()
                filterDict = { timesearchField + '__gt': today}
                qs = qs.filter(**filterDict)
        
        
            
        # TODO handle search with sphinx
        search = self.request.POST.get(u'search[value]', None)
        if search:
            self.buildQuery(str(search))
            tagsQuery = self.model.buildTagsQuery(search)
            if tagsQuery:
                self.addQuery(Q(**tagsQuery))
            if self.queries:
                qs = qs.filter(self.queries)
            noteQuery = self.model.buildNoteQuery(search)
            if noteQuery:
                qs = qs.filter(noteQuery)
        
        last = self.request.POST.get(u'last', -1)
        if last > 0:
            qs = qs[-last:]
        
        return qs.distinct()
    
def helpPopup(request, help_content_path, help_title):
    return render(request,
                  'help_popup.html',
                  {'help_title': help_title,
                   'help_content_path': help_content_path},
                  )

def addRelay(dataProduct, filesToSave, serializedForm, url, broadcast=True, update=False):
    # first see if there is an existing relayEvent
    content_type=ContentType.objects.get_for_model(dataProduct)
    object_id=dataProduct.pk
    
    #see if we already have an event for this type and PK, if we don't support updates to the same PK
    event = None
    if not update:
        try:
            if object_id.is_numeric():
                isExternal = DbServerInfo.keyFromExternalServer(object_id)
                if isExternal:
                    print 'You were trying to re-relay something from outside %s %d' % (content_type, object_id)
                    return
        except:
            pass

        # you are not updating, this should be a new relay event that you are either adding a file to or you'll have to make a new one
        existingEvents = RelayEvent.objects.filter(content_type=content_type, object_id=object_id)
        if existingEvents.count():
            event = existingEvents[0]
    
    if not event:
        try:
            acquisition_time = dataProduct.acquisition_time
        except:
            acquisition_time = timezone.now()
            
        event = RelayEvent(content_type=ContentType.objects.get_for_model(dataProduct),
                           object_id=dataProduct.pk,
                           acquisition_time=acquisition_time,
                           serialized_form=serializedForm,
                           url=url,
                           is_update=update)
        event.save()

    if filesToSave:
        for k,f in filesToSave.iteritems():
            relayFile = RelayFile(file_to_send=f,
                                  file_key=k,
                                  relay_event_id=event.pk)
            relayFile.save()
        
    #fire REDIS event if REDIS is on
    if settings.XGDS_CORE_REDIS and broadcast:
        #TODO insert delay if we have xgds_core_constant delay set, start a new thread
        delay = getDelay()
        if delay:
            # there is a delay
            t = threading.Timer(delay, fireRelay, [event])
            t.start()
        else:
            # there is no delay
            fireRelay(event)

def getDelay():
    try:
        return int(Constant.objects.get(name='delay').value)
    except:
        return 0

def fireRelay(event):
    queueRedisData(settings.XGDS_CORE_REDIS_RELAY_CHANNEL, event.toRelayJson())
    event.relay_start_time = datetime.datetime.utcnow()
    event.save()

def receiveRelay(request):
    object_id = request.POST.get('object_id')
    content_type_app_label = request.POST.get('content_type_app_label')
    content_type_model = request.POST.get('content_type_model')
    ct = ContentType.objects.get(model=content_type_model, app_label=content_type_app_label)
    
    if not request.POST.get('is_update'): 
        try:
            foundObject = ct.get_object_for_this_type(pk=object_id)
            
            # return success, we already have it
            return HttpResponse(json.dumps({'exists': 'true', 
                                            'json': {'pk': object_id,
                                                     'content_type_app_label': content_type_app_label,
                                                     'content_type_model': content_type_model}}), 
                                content_type='application/json')
            
        except:
            pass
        
    # either we are updating or 
    # we don't have this object already, call the original url to submit
    url = request.POST.get('url')
    serialized_form = request.POST.get('serialized_form')
    serialized_form_dict = json.loads(serialized_form)
    
    # add the original form information back to the request
    mutable = request.POST._mutable
    request.POST._mutable = True
    for k,v in serialized_form_dict.iteritems():
        request.POST[k]=v
    request.POST._mutable = mutable
    
    view, view_args, view_kwargs = resolve(url)
    if 'loginRequired' in view_kwargs:
        del view_kwargs['loginRequired']
    try:
        return view(request, **view_kwargs)
    except:
        traceback.print_exc()


CONDITION_MODEL = LazyGetModelByName(settings.XGDS_CORE_CONDITION_MODEL)
CONDITION_HISTORY_MODEL = LazyGetModelByName(settings.XGDS_CORE_CONDITION_HISTORY_MODEL)

    
def setCondition(request):
    ''' read information from request.POST and use it to set or update a stored condition
    '''
    try:
        raw_source_time = request.POST.get('time')
        source_time = dateparser(raw_source_time)
        condition_source = request.POST.get('source')
        condition_source_id = request.POST.get('id', None)
        if condition_source_id:
            condition, created = CONDITION_MODEL.get().objects.get_or_create(source=condition_source, source_id=condition_source_id)
        else:
            condition = CONDITION_MODEL.get()(source=condition_source)

        condition_data = request.POST.get('data', '{}')
        condition_history = condition.populate(source_time, condition_data)
        result = condition_history.broadcast()
#         json_condition_history = serialize('json', [condition, condition_history], use_natural_foreign_keys=True)
#         result = {'status': 'success',
#                   'data': json_condition_history}
#         
#         if settings.XGDS_SSE and settings.XGDS_CORE_REDIS:
#             publishRedisSSE(condition.getRedisSSEChannel(), 'condition', json_condition_history)

        return JsonResponse(result,status=httplib.ACCEPTED, encoder=DatetimeJsonEncoder)
    
    except Exception as e:
        traceback.print_exc()
        result_dict = {'status': 'error',
                       'error': str(e)
                       }
        return JsonResponse(json.dumps(result_dict),
                            status=httplib.NOT_ACCEPTABLE)


def getConditionActiveJSON(request, range=12, filter=None, filterDict={}):
    ''' Get the conditions from the last n hours, filtered by filter, in JSON
    '''
    now = datetime.datetime.now(pytz.utc)
    yesterday = now - datetime.timedelta(seconds=3600 * range)
    
    if filter:
        filterDict = buildFilterDict(filter)
    filterDict['source_time__lte'] = now
    filterDict['source_time__gte'] = yesterday

    
    recent_histories = None
    try:
        condition_ids = CONDITION_MODEL.get().objects.filter(start_time__lte=now).filter(start_time__gte=yesterday).values_list('pk', flat=True).distinct()
        if condition_ids:    
            recent_histories = [CONDITION_HISTORY_MODEL.get().objects.filter(**filterDict).filter(condition_id=c).order_by('-source_time')[0] for c in condition_ids]
    except:
        pass
        
    if recent_histories:
        serialize_list = []
        for h in recent_histories:
            serialize_list.append(h.condition)
            serialize_list.append(h)
        json_condition_history = serialize('json', serialize_list, use_natural_foreign_keys=True)
#         json_condition_history = serialize('json', recent_histories, use_natural_foreign_keys=True)
        return JsonResponse(json_condition_history, status=httplib.OK, encoder=DatetimeJsonEncoder, safe=False)
    
    else:
        return JsonResponse({}, status=httplib.NO_CONTENT)
        
    
def dataInsert(request, action, tablename, pk):
    if action == 'DELETE':
        return

    # if not see if the tablename maps to a supported broadcast model.
    if not tablename in settings.XGDS_CORE_REBROADCAST_MAP:
        return
    
    # TODO the data will not yet be in the database so instead we will stick this on a new REDIS queue
    # This will be used by yet another daemon with is the rebroadcast daemon (running with django)
    # That will read the action, tablename and pk off of redis queue and try to do the below functions
    # if the object exists in the db which it should by then it will be removed from redis queueif settings.XGDS_CORE_REDIS:
    if settings.XGDS_CORE_REDIS:
        queueRedisData(settings.XGDS_CORE_REDIS_REBROADCAST, json.dumps({'action':action, 'tablename': tablename, 'pk': pk}))
    
    # if so look up the model object instance from the table name and pk
    #modelname = settings.XGDS_CORE_REBROADCAST_MAP[tablename]['modelName']
    #LAZY_MODEL = LazyGetModelByName(modelname)
    
    # and then broadcast it
    #theModel = LAZY_MODEL.get().objects.get(pk=pk)
    #theModel.broadcast()
    
    result = {'data':'broadcast',
              'timestamp':datetime.datetime.now(pytz.utc)}
    return JsonResponse(result, encoder=DatetimeJsonEncoder)


def getRebroadcastTableNamesAndKeys(request):
    rebroadcastMap = settings.XGDS_CORE_REBROADCAST_MAP
    return JsonResponse(rebroadcastMap, safe=False)
    