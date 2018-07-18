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
import shlex
from dateutil.parser import parse as dateparser

from django.utils import timezone
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.db.utils import IntegrityError
from django.core.exceptions import ObjectDoesNotExist

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

from geocamUtil.loader import LazyGetModelByName, getModelByName
from geocamUtil.datetimeJsonEncoder import DatetimeJsonEncoder

from xgds_core.models import TimeZoneHistory, DbServerInfo, Constant, RelayEvent, RelayFile
from xgds_notes2.utils import buildQueryForTags
from xgds_notes2.models import HierarchichalTag
from xgds_core.models import TimeZoneHistory, DbServerInfo, Constant, RelayEvent, RelayFile, State
from xgds_core.flightUtils import create_group_flight
if settings.XGDS_CORE_REDIS:
    from xgds_core.redisUtil import queueRedisData, publishRedisSSEAtTime

ACTIVE_FLIGHT_MODEL = LazyGetModelByName(settings.XGDS_CORE_ACTIVE_FLIGHT_MODEL)
FLIGHT_MODEL = LazyGetModelByName(settings.XGDS_CORE_FLIGHT_MODEL)
GROUP_FLIGHT_MODEL = LazyGetModelByName(settings.XGDS_CORE_GROUP_FLIGHT_MODEL)
VEHICLE_MODEL = LazyGetModelByName(settings.XGDS_CORE_VEHICLE_MODEL)


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

    # to hold the Q queries for and-ing/or-ing a keyword search
    keywordQueries = None

    # to hold the query with the found objects which have notes that have content that matches on the keyword search
    noteContentResults = None

    # to hold the Q queries for and-ing/or-ing a tag search
    tagQueries = None
    
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

    def addOrQuery(self, queries, query):
        if queries:
            queries |= query
        else:
            queries = query
        return queries

    def addAndQuery(self, query):
        if self.formQueries:
            self.formQueries &= query
        else:
            self.formQueries = query

    # Adds keyword queries together based on the connecting words between them (and/or)
    def addKeywordQuery(self, query, type):
        if self.keywordQueries and query and type == "and":
            self.keywordQueries &= query
        elif self.keywordQueries and query and type == "or":
            self.keywordQueries |= query
        else:
            self.keywordQueries = query

    # Adds tag queries together based on the connecting words between them (and/or)
    def addTagQuery(self, query, type):
        if self.tagQueries and query and type == "and":
            self.tagQueries &= query
        elif self.tagQueries and query and type == "or":
            self.tagQueries |= query
        else:
            self.tagQueries = query

    # Builds the queries for each searchable field for that model (all or-ed together)
    def buildSearchableFieldsQuery(self, search):
        if search:
            queries = None
            try:
                for key in self.model.getSearchableFields():
                    queries = self.addOrQuery(queries, Q(**{key + '__icontains': search}))

                if unicode(search).isnumeric():
                    for key in self.model.getSearchableNumericFields():
                        queries = self.addOrQuery(queries, Q(**{key: search}))
            except:
                try:
                    self.model._meta.get_field('name')
                    queries = self.addOrQuery(queries, Q(**{'name__icontains': search}))
                except:
                    pass

                try:
                    self.model._meta.get_field('description')
                    queries = self.addOrQuery(queries, Q(**{'description__icontains': search}))
                except:
                    pass

            return queries

    # Builds the query for checking if a note contains a certain tag pk
    def buildTagQuery(self, tagId, nestTags):
        query = None
        if tagId:
            taggedNote = LazyGetModelByName(settings.XGDS_NOTES_TAGGED_NOTE_MODEL)
            model = self.request.POST.get(u'modelName', None)

            if model == settings.XGDS_NOTES_NOTE_MONIKER:
                query = Q(**{'notes__in': taggedNote.get().objects.filter(tag_id__in=[tagId])})
            else:
                # Nest tags is not checked
                if nestTags == "false":
                    query = Q(**{'notes__in': taggedNote.get().objects.filter(tag_id__in=[tagId]).values('content_object')})
                # Nest tags so search by HierarchichalTags
                else:
                    tag = HierarchichalTag.objects.get(pk=tagId)
                    tagqs = tag.get_tree(tag)
                    query = Q(**{'notes__in': taggedNote.get().objects.filter(tag__in=tagqs).values('content_object')})

        return query

    def buildFilterDict(self, theFilter):
        dictEntries = str(theFilter).split(",")
        for entry in dictEntries:
            splits = str(entry).split("|")
            try:
                value = int(splits[1])
                self.filterDict[splits[0]] = value
            except:
                self.filterDict[splits[0]] = splits[1]

    # Overrides the django_datatables filter_queryset function.
    # Does either advanced search or simple search depending on values passed
    def filter_queryset(self, qs):
        model = self.request.POST.get(u'modelName', None)
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
        if model == settings.XGDS_NOTES_NOTE_MONIKER:
            tags = self.request.POST.getlist('noteTags[]')
        else:
            tags = self.request.POST.get(u'tags', None)

        # This part handles the search with the input boxes above the datatable
        if self.request.POST.get(u'simpleSearch', None):
            qs = self.filter_queryset_simple_search(qs, search, tags)

        last = self.request.POST.get(u'last', -1)
        if last > 0:
            qs = qs[-last:]

        return qs.distinct()

    # Filter a queryset using the keyword and tag search inputs above the datatable
    def filter_queryset_simple_search(self, qs, search, tags):
        self.keywordQueries = None
        self.tagQueries = None
        if search and len(search) > 0:
            self.filter_keyword_search(qs, search)

        if tags and len(tags) > 0:
            self.filter_tags_search(qs, tags)

        queries = self.combine_simple_search()
        if queries:
            qs = qs.filter(queries)

        return qs

    # Filters the queryset with the advanced search (everything is anded)
    def filter_queryset_advanced_search(self, qs, searchDict):
        if searchDict:
            for key in searchDict:
                if unicode(searchDict[key]).isnumeric():
                    self.addAndQuery(Q(**{key: searchDict[key]}))
                else:
                    self.addAndQuery(Q(**{key + '__icontains': searchDict[key]}))
            qs = qs.filter(self.formQueries)

        return qs.distinct()

    def combine_simple_search(self):
        """
        Combines keyword with tag search via the and/or between the two inputs
        :return:
        """

        connector = self.request.POST.get(u'connector', None)
        if not self.keywordQueries and not self.tagQueries and not self.noteContentResults:
            return None

        elif not self.tagQueries:
            # we have only keyword queries
            if self.noteContentResults:
                return self.keywordQueries | self.noteContentResults
            else:
                return self.keywordQueries
        elif not self.keywordQueries:
            return self.tagQueries
        else:
            # we have both keyword and tag queries
            if connector == "or":
                # TODO this is slow; we tried various things but don't know why
                if self.noteContentResults:
                    return self.noteContentResults | self.tagQueries | self.keywordQueries
                else:
                    return self.tagQueries | self.keywordQueries
            else:
                # and connector
                if self.noteContentResults:
                    return (self.tagQueries & self.keywordQueries) | (self.noteContentResults & self.tagQueries)
                else:
                    return self.tagQueries & self.keywordQueries

    # Creates the keyword queries to be used on the queryset
    def filter_keyword_search(self, qs, search):
        model = self.request.POST.get(u'modelName', None)
        model_class = None
        if model:
            model_class = getModelByName(settings.XGDS_MAP_SERVER_JS_MAP[model]['model'])

        noteQuery = None
        words = []
        counter = 0
        if " " in search:
            words = shlex.split(search)
        else:
            words.append(search)

        # Adds the individual queries for each word into an array
        fieldsQuery = None
        keywordQueriesArray = []
        keywords = []

        # Loop through the words and construct a list of queries based on each keyword.
        # The words will be something like
        # KEYWORD OR KEYWORD OR KEYWORD
        # KEYWORD AND KEYWORD AND KEYWORD
        # KEYWORD AND KEYWORD OR KEYWORD
        # note we don't support parens yet
        # we are building arrays where it is [Q, 'and', Q, 'or' ...]
        while counter < len(words):
            if counter % 2 == 0:
                keywords.append(str(words[counter]))
                fieldsQuery = self.buildSearchableFieldsQuery(str(words[counter]))
                keywordQueriesArray.append(fieldsQuery)
            else:
                keywordQueriesArray.append(str(words[counter]))

            counter += 1

        # Combines the queries at each index in the array based on and/or
        counter = 0
        while counter < len(keywordQueriesArray):
            if counter == 0:
                self.addKeywordQuery(keywordQueriesArray[counter], "")
            else:
                self.addKeywordQuery(keywordQueriesArray[counter], keywordQueriesArray[counter - 1])
            counter += 2

        # for text search in note content for relevant notes
        found_object_ids = self.model.buildNoteQuery(words, model_class)
        if found_object_ids:
            self.noteContentResults = Q(**{'id__in': found_object_ids})

        return self.keywordQueries

    # Creates the tag queries to be used on the queryset
    def filter_tags_search(self, qs, tags):
        model = self.request.POST.get(u'modelName', None)
        nestTags = self.request.POST.get(u'nestTags', None)
        counter = 0
        tagQueriesArray = []

        # Adds the individual queries for each tag into an array
        if model == settings.XGDS_NOTES_NOTE_MONIKER:
            while (counter < len(tags)):
                if (counter % 2 == 0):
                    tagQuery = self.model.buildTagsQuery(tags[counter])
                    if tagQuery:
                        tagQuery = Q(**tagQuery)
                        tagQueriesArray.append(tagQuery)
                else:
                    tagQueriesArray.append(tags[counter])
                counter += 1
        else:
            tagArray = []
            if "," in tags:
                tagArray = tags.split(",")
            else:
                tagArray.append(tags)

            while counter < len(tagArray):
                if counter % 2 == 0:
                    tagQuery = self.buildTagQuery(tagArray[counter], nestTags)
                    tagQueriesArray.append(tagQuery)
                else:
                    connector = str(tagArray[counter]).split("-")
                    tagQueriesArray.append(connector[0])
                counter += 1

        # Combines the queries at each index in the array based on and/or
        counter = 0
        while counter < len(tagQueriesArray):
            if counter == 0:
                self.addTagQuery(tagQueriesArray[counter], "")
            else:
                self.addTagQuery(tagQueriesArray[counter], tagQueriesArray[counter - 1])
            counter += 2

        return self.tagQueries


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
            object_pk_int = int(object_id)
            isExternal = DbServerInfo.keyFromExternalServer(object_pk_int)
            if isExternal:
                print 'You were trying to re-relay something from outside %s %d' % (content_type, object_pk_int)
                return
        except:
            print 'Relay problem, CHECK YOUR DATABASE FOR GLOBAL VARIABLES not update and object id is %s' % object_id
            traceback.print_exc()
            pass

        # you are not updating, this should be a new relay event that you are either adding a file to or you'll have to make a new one
        existingEvents = RelayEvent.objects.filter(content_type=content_type, object_id=object_id, hostname=settings.HOSTNAME)
        if existingEvents.count():
            event = existingEvents[0]
    
    if not event:
        try:
            acquisition_time = dataProduct.acquisition_time
        except:
            acquisition_time = timezone.now()
            
        event = RelayEvent(content_type=content_type,
                           object_id=object_id,
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
    event.relay_start_time = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
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
    try:
        for k,v in serialized_form_dict.iteritems():
            request.POST[k]=v
    except:
        pass
    request.POST._mutable = mutable
    
    view, view_args, view_kwargs = resolve(url)
#     if 'loginRequired' in view_kwargs:
#         del view_kwargs['loginRequired']
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
            conditions = CONDITION_MODEL.get().objects.filter(source=condition_source, source_id=condition_source_id)
            if not conditions:
                condition = CONDITION_MODEL.get()(source=condition_source, source_id=condition_source_id)
            else:
                condition = conditions.last()
        else:
            condition = CONDITION_MODEL.get()(source=condition_source)

        condition_data = request.POST.get('data', '{}')
        condition_history = condition.populate(source_time, condition_data)
        result = condition_history.broadcast()

        return JsonResponse(result,status=httplib.ACCEPTED, encoder=DatetimeJsonEncoder, safe=False)
    
    except Exception as e:
        traceback.print_exc()
        result_dict = {'status': 'error',
                       'error': str(e)
                       }
        return JsonResponse(json.dumps(result_dict),
                            status=httplib.NOT_ACCEPTABLE, safe=False)


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



def rebroadcastSse(request):
    ''' Receive some json information which will allow us to reflect this information on our SSE channels 
    We will inject delay if we are running in delay.
    '''
    if settings.XGDS_CORE_REDIS and settings.XGDS_SSE:
        if request.method=='POST':
            channel = request.POST.get('channel')
            sseType = request.POST.get('sseType')
            jsonString = request.POST.get('jsonString')

            # figure out when we want to publish this
            eventTimeString = request.POST.get('eventTime')
            delay = getDelay()
            eventTime = dateparser(eventTimeString)
            publishTime = eventTime + datetime.timedelta(seconds=delay)

            publishRedisSSEAtTime(channel, sseType, jsonString, publishTime)
            
            result = {'data':'broadcast',
                      'timestamp':datetime.datetime.now(pytz.utc)}
            return JsonResponse(result, encoder=DatetimeJsonEncoder)

    result = {'data':'fail broadcast',
              'timestamp':datetime.datetime.now(pytz.utc)}
    return JsonResponse(result, encoder=DatetimeJsonEncoder, status=406)


def getSseActiveConditions(request):
    # Look up the active conditions we are using for SSE
    return JsonResponse(settings.XGDS_SSE_CONDITION_CHANNELS, safe=False)


def setState(key, start=None, end=None, values=None, active=True, notes=None):
    """
    Store or modify a state in the database.  If you are modifying, it will only pass changes in if they are not none
    in parameters.
    :param key: A unique key representing this state, for example flight name.  Defaults to isotime
    :param start: start time of this state
    :param end: end time of this state
    :param values: a dictionary of values to store as JSON.  Must be serializable
    :param active: boolean for if this is currently active
    :param notes: optional descriptive notes
    :return: the state.
    """

    rightnow = timezone.now()
    if not key:
        key = rightnow.isoformat()
    created = False
    try:
        state = State.objects.get(key=key)
    except:
        created = True
        if not start:
            start = rightnow
        state = State(key=key, start=start, end=end, notes=notes, active=active)

    if not created:
        if start:
            state.start = start
        if end:
            state.end = end
        if notes:
            state.notes = notes
        state.active = active

    if values:
        state.values = json.dumps(values, cls=DatetimeJsonEncoder, separators=(',',':'), indent=0)
    state.dateModified = rightnow
    state.save()

    return state


def getState(key):
    """
    Get the state given the key
    :param key:
    :return: the state, or None
    """
    try:
        return State.objects.get(key=key)
    except:
        pass
    return None


def getActiveStates():
    """
    Get the active states
    :return: the active states, or None
    """
    return State.objects.filter(active=True).all()


def endActiveStates():
    """
    End all the active states, setting end time to now and active to false
    :return: the number of states ended.
    """
    rightnow = timezone.now()
    active_states = getActiveStates()
    count = len(active_states)
    for state in active_states:
        setState(state.key, start=None, end=rightnow, active=False)
    return count


# Flight support, ported over from planner

def processNameToDate(flight):
    result = {}
    if (len(flight.name) >= 8):
        year = flight.name[0:4].encode()
        month = flight.name[4:6].encode()
        day = flight.name[6:8].encode()
        result = {"year": year, "month": month, "day": day}
    return result


def getGroupFlights():
    return GROUP_FLIGHT_MODEL.get().objects.exclude(name="").order_by('name')


def getAllFlights(today=False, reverseOrder=False):
    orderby = 'name'
    if reverseOrder:
        orderby = '-name'
    if not today:
        return FLIGHT_MODEL.get().objects.all().order_by(orderby)
    else:
        now = timezone.localtime(datetime.datetime.now(pytz.utc))
        todayname = "%04d%02d%02d" % (now.year, now.month, now.day)
        return FLIGHT_MODEL.get().objects.filter(name__startswith=(todayname)).order_by(orderby)


def getAllGroupFlights(today=False, reverseOrder=False):
    orderby = 'name'
    if reverseOrder:
        orderby = '-name'
    if not today:
        return GROUP_FLIGHT_MODEL.get().objects.all().order_by(orderby)
    else:
        now = timezone.localtime(datetime.datetime.now(pytz.utc))
        todayname = "%04d%02d%02d" % (now.year, now.month, now.day)
        return GROUP_FLIGHT_MODEL.get().objects.filter(name__startswith=(todayname)).order_by(orderby)


def getAllFlightNames(year="ALL", onlyWithPlan=False, reverseOrder=True):
    orderby = 'name'
    if reverseOrder:
        orderby = '-name'
    flightList = FLIGHT_MODEL.get().objects.exclude(name="").order_by(orderby)
    flightNames = ["-----"]
    if flightList:
        for flight in flightList:
            if (flight.name):
                flightNames.append(flight.name)
    return flightNames


def manageFlights(request, errorString=""):
    today = request.session.get('today', False)
    return render(request,
                  "xgds_core/ManageFlights.html",
                  {'groups': getAllGroupFlights(today=today),
                   'title': settings.XGDS_CORE_FLIGHT_MONIKER,
                   'help_content_path': 'xgds_core/help/manageFlights.rst',
                   "errorstring": errorString},
                  )


def listFlownFlights(request, errorString=""):
    today = request.session.get('today', False)
    return render(request,
                  "xgds_core/ListFlownFlights.html",
                  {'groups': getAllGroupFlights(today=today),
                   'title': settings.XGDS_CORE_FLIGHT_MONIKER,
                   'help_content_path': 'xgds_core/help/manageFlights.rst',
                   "errorstring": errorString},
                  )


def startFlightTracking(request, flightName):
    try:
        flight = FLIGHT_MODEL.get().objects.get(name=flightName)
        if settings.GEOCAM_TRACK_SERVER_TRACK_PROVIDER:
            flight.startTracking()
            messages.info(request, "Tracking started: " + flightName)
        else:
            messages.error(request, "This server is not a tracking provider")
    except FLIGHT_MODEL.get().DoesNotExist:
        messages.error(request, 'Flight not found: ' + flightName)
    return redirect(reverse('error'))


def stopFlightTracking(request, flightName):
    try:
        flight = FLIGHT_MODEL.get().objects.get(name=flightName)
        if settings.GEOCAM_TRACK_SERVER_TRACK_PROVIDER:
            flight.stopTracking()
            messages.info(request, "Tracking stopped: " + flightName)
        else:
            messages.error(request, "This server is not a tracking provider")
    except FLIGHT_MODEL.get().DoesNotExist:
        messages.error(request, 'Flight not found: ' + flightName)
    return redirect(reverse('error'))


def startFlight(request, uuid):
    errorString = ""
    try:
        flight = FLIGHT_MODEL.get().objects.get(uuid=uuid)
        # This next line is to avoid replication problems. If we are not the track provider (e.g. ground server) we wait for times to replicate.
        if settings.GEOCAM_TRACK_SERVER_TRACK_PROVIDER:
            if not flight.start_time:
                flight.start_time = datetime.datetime.now(pytz.utc)
            flight.end_time = None
            flight.save()
    except FLIGHT_MODEL.get().DoesNotExist:
        errorString = "Flight not found"

    if flight:
        # end any other active flight that is with the same vehicle
        try:
            conflictingFlights = ACTIVE_FLIGHT_MODEL.get().objects.filter(flight__vehicle__pk=flight.vehicle.pk)
            for cf in conflictingFlights:
                doStopFlight(request, cf.flight.uuid)
        except:
            pass

        # make this flight active
        foundFlight = ACTIVE_FLIGHT_MODEL.get().objects.filter(flight__pk=flight.pk)
        if not foundFlight:
            newlyActive = ACTIVE_FLIGHT_MODEL.get()(flight=flight)
            newlyActive.save()

        flight.startFlightExtras(request)

        setState(flight.name, flight.start_time, values=model_to_dict(flight), notes='Flight Started')

    return manageFlights(request, errorString)


def stopFlight(request, uuid):
    errorString = doStopFlight(request, uuid)
    return manageFlights(request, errorString)


def doStopFlight(request, uuid):
    errorString = ""
    try:
        flight = FLIGHT_MODEL.get().objects.get(uuid=uuid)
        if not flight.start_time:
            errorString = "Flight has not been started"
        else:
            flight.end_time = datetime.datetime.now(pytz.utc)
            flight.save()
            try:
                flight.stopFlightExtras(request, flight)
            except:
                print 'error in stop flight extras for %s' % flight.name
                traceback.print_exc()

            # kill the plans
            for pe in flight.plans.all():
                if pe.start_time:
                    pe.end_time = flight.end_time
                    pe.save()
            try:
                active = ACTIVE_FLIGHT_MODEL.get().objects.get(flight__pk=flight.pk)
                active.delete()
            except ObjectDoesNotExist:
                errorString = 'Flight IS NOT ACTIVE'

            setState(flight.name, end=flight.end_time, active=False, notes='Flight Ended')

    except:
        traceback.print_exc()
        errorString = "Flight not found"
    return errorString


def addGroupFlight(request):
    from xgds_core.forms import GroupFlightForm
    group_flight = None
    errorString = ''

    if request.method != 'POST':
        groupFlightForm = GroupFlightForm()
        return render(request,
                      "xgds_core/AddGroupFlight.html",
                      {'groupFlightForm': groupFlightForm,
                       'groupFlights': getGroupFlights(),
                       'errorstring': errorString})

    if request.method == 'POST':
        form = GroupFlightForm(request.POST)
        group_flight = None
        if form.is_valid():
            try:
                group_flight_name = form.cleaned_data['date'].strftime('%Y%m%d') + form.cleaned_data['prefix']
                vehicles = []
                vModel = VEHICLE_MODEL.get()
                for vehicle_name in form.cleaned_data['vehicles']:
                    vehicles.append(vModel.objects.get(name=vehicle_name))

                group_flight = create_group_flight(group_flight_name, form.cleaned_data['notes'], vehicles)

            except IntegrityError, strerror:
                return render(request,
                              "xgds_core/AddGroupFlight.html",
                              {'groupFlightForm': form,
                               'groupFlights': getGroupFlights(),
                               'errorstring': "Problem Creating Group Flight: {%s}" % strerror},
                              )
        else:
            errorString = form.errors
            return render(request,
                          "xgds_core/AddGroupFlight.html",
                          {'groupFlightForm': form,
                           'groupFlights': getGroupFlights(),
                           'errorstring': errorString},
                          )

    # add relay ...
    if group_flight:
        addRelay(group_flight, None,
                 json.dumps({'name': group_flight.name, 'id': group_flight.pk, 'notes': group_flight.notes}),
                 reverse('xgds_core_relayAddGroupFlight'))
        for f in group_flight.flights.all():
            addRelay(f, None, json.dumps(
                {'group_id': group_flight.pk, 'vehicle_id': f.vehicle.pk, 'name': f.name, 'uuid': str(f.uuid),
                 'id': f.id}), reverse('xgds_core_relayAddFlight'))

    return HttpResponseRedirect(reverse('xgds_core_manage', args=[]))


def relayAddFlight(request):
    """ Add a flight with same pk and uuid from the post dictionary
    """
    try:
        try:
            flightName = request.POST.get('name')
            preexisting = FLIGHT_MODEL.get().get(name=flightName)
            preexisting.name = 'BAD' + preexisting.name
            preexisting.save()

            # TODO this should never happen, we should not have flights on multiple servers with the same name
            print '********DUPLICATE FLIGHT***** %s WAS ATTEMPTED TO RELAY WITH PK %d' % (
            flightName, request.POST.get('id'))
        except:
            pass

        # we are good it does not exist
        form_dict = json.loads(request.POST.get('serialized_form'))
        newFlight = FLIGHT_MODEL.get()(**form_dict)
        newFlight.save()
        return JsonResponse(model_to_dict(newFlight))
    except Exception, e:
        traceback.print_exc()
        return JsonResponse({'status': 'fail', 'exception': str(e)}, status=406)


def relayAddGroupFlight(request):
    """ Add a group flight with same pk and uuid from the post dictionary
    """
    try:
        try:
            gfName = request.POST.get('name')
            preexisting = GROUP_FLIGHT_MODEL.get().get(name=gfName)
            preexisting.name = 'BAD' + preexisting.name
            preexisting.save()
            # TODO this should never happen, we should not have flights on multiple servers with the same name
            print '********DUPLICATE GROUP FLIGHT***** %s WAS ATTEMPTED TO RELAY WITH PK %d' % (
            gfName, request.POST.get('id'))
        except:
            pass

        form_dict = json.loads(request.POST.get('serialized_form'))
        newGroupFlight = GROUP_FLIGHT_MODEL.get()(**form_dict)
        newGroupFlight.save()
        return JsonResponse(model_to_dict(newGroupFlight))
    except Exception, e:
        traceback.print_exc()
        return JsonResponse({'status': 'fail', 'exception': str(e)}, status=406)


def getActiveFlights(vehicle=None):
    ACTIVE_FLIGHTS_MODEL = LazyGetModelByName(settings.XGDS_CORE_ACTIVE_FLIGHT_MODEL)

    if not vehicle:
        return ACTIVE_FLIGHTS_MODEL.get().objects.all()
    else:
        # filter by vehicle
        return ACTIVE_FLIGHTS_MODEL.get().objects.filter(flight__vehicle=vehicle)


def getActiveFlightFlights(vehicle=None):
    activeFlights = getActiveFlights(vehicle)
    flights = FLIGHT_MODEL.get().objects.filter(active__in=activeFlights)
    return flights


def activeFlightsTreeNodes(request):
    activeFlights = getActiveFlights()
    result = []
    for aFlight in activeFlights:
        result.append(aFlight.flight.getTreeJson())
    json_data = json.dumps(result, indent=4)
    return HttpResponse(content=json_data,
                        content_type="application/json")


def completedFlightsTreeNodes(request):
    flights = FLIGHT_MODEL.get().objects.exclude(end_time__isnull=True)
    result = []
    for f in flights:
        result.append(f.getTreeJson())
    json_data = json.dumps(result, indent=4)
    return HttpResponse(content=json_data,
                        content_type="application/json")


def flightTreeNodes(request, flight_id):
    flight = FLIGHT_MODEL.get().objects.get(id=flight_id)
    json_data = json.dumps(flight.getTreeJsonChildren(), indent=4)
    return HttpResponse(content=json_data,
                        content_type="application/json")


def getTodaysGroupFlights():
    today = timezone.localtime(timezone.now()).date()
    return GROUP_FLIGHT_MODEL.get().objects.filter(name__startswith=today.strftime('%Y%m%d'))


def getGroupFlightSummary(request, groupFlightName):
    try:
        group = GROUP_FLIGHT_MODEL.get().objects.get(name__startswith=groupFlightName)
        return render(request,
                      "xgds_core/groupFlightSummary.html",
                      {'groupFlight': group},
                      )
    except ObjectDoesNotExist:
        raise Http404("%s %s does not exist" % (settings.XGDS_CORE_GROUP_FLIGHT_MONIKER, groupFlightName))


def updateTodaySession(request):
    if not request.is_ajax() or not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
    todayChecked = request.POST.get('today')
    todayValue = todayChecked == unicode('true')
    request.session['today'] = todayValue
    return HttpResponse('ok')
