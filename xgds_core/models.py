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
import json
import datetime
from dateutil.parser import parse as dateparser

from django.utils import timezone
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from geocamUtil.models.ExtrasDotField import ExtrasDotField
from geocamUtil.loader import LazyGetModelByName

from xgds_core.util import get100Years


class Constant(models.Model):
    name = models.CharField(max_length=64, blank=False)
    units = models.CharField(max_length=32, blank=False)
    notes = models.CharField(max_length=256, blank=False)
    dataType = models.CharField(max_length=32, blank=False)
    value = models.CharField(max_length=256, blank=False)

    def __unicode__(self):
        return u'%s: %s' % (self.name, self.value)
    
    
class TimeZoneHistory(models.Model):
    startTime = models.DateTimeField(default=timezone.now)
    endTime = models.DateTimeField(null=True, blank=True, default=get100Years )
    timeZone = models.CharField(max_length=128, blank=False)
    notes = models.CharField(max_length=512, blank=True)
    
    
class XgdsUser(User):
    class Meta:
        proxy = True
        ordering = ['first_name']
    
    @classmethod
    def getAutocompleteFields(cls):
        return ['first_name', 'last_name']

    def __unicode__(self):
        return u'%s %s' % (self.first_name, self.last_name)


class NamedURL(models.Model):
    name = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    url = models.CharField(max_length=1024, blank=False, null=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')


class SearchableModel(object):
    """
    Mixin this class to have your model get the methods it needs to be searchable and
    show up in the datatables.
    Override methods where you need to.
    """
    
    @property
    def DT_RowId(self):
        return self.pk
    
    def renderColumn(self, column):
        text = None
        try:
            text = getattr(self, column)
        except AttributeError:
            for part in column.split('.'):
                obj = getattr(self, part)
            text = obj
        if text is None:
            text = ''
        return text
    
    def toMapList(self, columns):
        """
        Return a list of the values for rendering in tables or on the map
        """
        return [self.renderColumn(column) for column in columns]
    
    def toMapDict(self):
        """
        Return a reduced dictionary that will be turned to JSON for rendering in a map
        """
        columns = settings.XGDS_MAP_SERVER_JS_MAP[self.cls_type()]['columns']
        values =  self.toMapList(columns)
        result = dict(zip(columns, values))
        return result
    
    @property
    def app_label(self):
        return self._meta.app_label
    
    @classmethod
    def cls_type(cls):
        #IMPORTANT -- override this if it is not the registered model name in site settings JS_MAP
        return cls._meta.object_name
    
    @property
    def type(self):
        return self.__class__.cls_type()
    
    @property
    def model_type(self):
        t = type(self)
        if self.get_deferred_fields():
            t = t.__base__
        return t._meta.object_name
    
    @property
    def view_url(self):
        return reverse('search_map_single_object', kwargs={'modelPK':self.pk,
                                                           'modelName': self.type})

    @property
    def lat(self):
        ''' latitude '''
        position = self.getPosition()
        if position:
            return position.latitude
        
    @property
    def lon(self):
        ''' longitude '''
        position = self.getPosition()
        if position:
            return position.longitude

    @property
    def alt(self):
        ''' altitude '''
        try:
            position = self.getPosition()
            if position:
                return position.altitude
        except:
            pass
        return None
    
    @property
    def head(self):
        ''' heading '''
        try:
            position = self.getPosition()
            if position:
                return position.heading
        except:
            pass
        return None
    
 
    def getPosition(self):
        if self.position:
            return self.position
        return None

    @classmethod
    def getSearchableFields(self):
        return ['name', 'description']
    
    @classmethod
    def getSearchableNumericFields(self):
        return []
    
    @classmethod
    def timesearchField(self):
        """ Override to return the name of the field that contains the most important searchable time"""
        return 'event_time'
    
    @property
    def tz(self):
        return self.timezone

    @classmethod
    def buildTagsQuery(cls, search_value):
        return None

    @classmethod
    def buildNoteQuery(cls, search_value):
        return None
    
def getRelayFileName(instance, filename):
    return settings.XGDS_CORE_RELAY_SUBDIRECTORY + filename

class RelayEvent(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    acquisition_time = models.DateTimeField(editable=False, null=True, blank=True, db_index=True)
    relay_start_time = models.DateTimeField(editable=False, null=True, blank=True, db_index=True)
    relay_success_time = models.DateTimeField(editable=False, null=True, blank=True, db_index=True)
    serialized_form = models.TextField()
    url = models.CharField(max_length=128)
    
    def getSerializedData(self):
        result = {'object_id':self.object_id,
                  'content_type_app_label': self.content_type.app_label,
                  'content_type_model': self.content_type.model,
                  'url': self.url,
                  'serialized_form': self.serialized_form}
        return result
    
    def toRelayJson(self):
        result = {'relay_event_pk': self.pk}
        return json.dumps(result)

class RelayFile(models.Model):
    file_to_send = models.FileField(upload_to=getRelayFileName, max_length=256)
    file_key = models.CharField(max_length=64)
    relay_event = models.ForeignKey(RelayEvent)

CONDITION_HISTORY_MODEL = LazyGetModelByName(settings.XGDS_CORE_CONDITION_HISTORY_MODEL)

class AbstractCondition(models.Model):
    source = models.CharField(null=False, blank=False, max_length=64, db_index=True)     # where did this condition originate
    source_id = models.CharField(null=True, blank=True, max_length=64, db_index=True)    # id from the source side so we can correlate or update conditions
    xgds_id = models.CharField(null=True, blank=True, max_length=64, db_index=True)      # id on the xGDS side in case we want to map this condition to something
    timezone = models.CharField(null=True, blank=False, max_length=32, default=settings.TIME_ZONE, db_index=True)    # timezone of the condition (for display)
    start_time = models.DateTimeField(editable=False, null=True, blank=True, db_index=True) # if the condition has a duration, what is its start time
    end_time = models.DateTimeField(editable=False, null=True, blank=True, db_index=True)   # if the condition has a duration, what is its end time
    name = models.CharField(null=True, blank=True, max_length=64)      # name which probably came from the source
    
    class Meta:
        abstract = True

    # In User class declaration
    @classmethod
    def create(cls, condition_source, condition_source_id):
        return cls(source=condition_source, 
                   source_id=condition_source_id)
    
    def populate(self, source_time, condition_data):
        ''' Fill in condition data and create a new condition history '''
        condition_data_dict = json.loads(condition_data)
        if 'xgds_id' in condition_data_dict:
            self.xgds_id = condition_data_dict['xgds_id']
        if 'name' in condition_data_dict:
            self.name = condition_data_dict['name']
        
        if 'timezone' in condition_data_dict:
            self.timezone = condition_data_dict['timezone']
        if 'start_time' in condition_data_dict:
            try:
                self.start_time = dateparser(condition_data_dict['start_time'])
            except:
                pass
        if 'end_time' in condition_data_dict:
            try:
                self.end_time = dateparser(condition_data_dict['end_time'])
            except:
                pass
    
        self.save()
        
        #create relevant condition history
        if 'status' in condition_data_dict:
            status = condition_data_dict['status']
        else:
            status = None
        condition_history = CONDITION_HISTORY_MODEL.get()(condition=self,
                                                          source_time=source_time,
                                                          status=status,
                                                          jsonData=condition_data)
        condition_history.populate(condition_data_dict)
        return condition_history
  
    def getLatestHistory(self):
        history = self.getHistory()
        lastCondition = history.last()
        if lastCondition:
            return lastCondition
        return None

    def getLatestStatus(self):
        lastCondition = self.getLatestHistory()
        if lastCondition:
            return lastCondition.status
        return None

    def getLatestSourceTime(self):
        lastCondition = self.getLatestHistory()
        if lastCondition:
            return lastCondition.source_time
        return None
    
    def getHistory(self):
        history_name = settings.XGDS_CORE_CONDITION_HISTORY_MODEL.replace('.','_')
        return getattr(self, history_name)
    


class Condition(AbstractCondition):
    pass

DEFAULT_CONDITION_FIELD = lambda: models.ForeignKey('xgds_core.Condition', null=True, blank=True)

class AbstractConditionHistory(models.Model):
    condition = 'set to DEFAULT_CONDITION_FIELD() or similar in derived classes'
    source_time = models.DateTimeField(editable=False, null=False, blank=False, db_index=True, default=timezone.now) # actual source time of the condition
    creation_time = models.DateTimeField(editable=False, null=False, blank=False, db_index=True, default=timezone.now)  # when was this modified in xGDS
    status = models.CharField(null=True, blank=True, max_length=128)    # id on the xGDS side in case we want to map this condition to something
    jsonData = ExtrasDotField(null=True, blank=True)                    # dot dictionary to hold the raw data and any extra data

    def populate(self, condition_data_dict, save=True):
        if save:
            self.save()

    class Meta:
        abstract = True
        ordering = ['creation_time']


class ConditionHistory(AbstractConditionHistory):
    condition = DEFAULT_CONDITION_FIELD()
