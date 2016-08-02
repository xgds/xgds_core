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
from django.utils import timezone
from django.db import models
from xgds_core.util import get100Years
from django.conf import settings
from django.core.urlresolvers import reverse

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

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
        
    def __unicode__(self):
        return u'%s, %s' % (self.first_name, self.last_name)


class NamedURL(models.Model):
    name = models.CharField(max_length=256, blank=True, null=True, db_index=True)
    url = models.CharField(max_length=1024, blank=False, null=False, db_index=True)
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
        if t._deferred:
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
