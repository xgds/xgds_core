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
import json
from dateutil.parser import parse as dateparser

from django.utils import timezone
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.urlresolvers import reverse

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.core.serializers import serialize

from geocamUtil.models.ExtrasDotField import ExtrasDotField
from geocamUtil.loader import LazyGetModelByName
from geocamUtil.datetimeJsonEncoder import DatetimeJsonEncoder
from geocamUtil.models.UuidField import UuidModel

from xgds_core.util import get100Years
from xgds_core.redisUtil import callRemoteRebroadcast
from fastkml import kml, styles
from shapely.geometry import Point, LineString, Polygon

if settings.XGDS_CORE_REDIS and settings.XGDS_SSE:
    from xgds_core.redisUtil import publishRedisSSE


class Constant(models.Model):
    name = models.CharField(max_length=64, blank=False)
    units = models.CharField(max_length=32, blank=False)
    notes = models.CharField(max_length=256, blank=True, null=True)
    dataType = models.CharField(max_length=32, blank=False)
    value = models.CharField(max_length=256, blank=False)

    def __unicode__(self):
        return u'%s: %s' % (self.name, self.value)


class TimeZoneHistory(models.Model):
    startTime = models.DateTimeField(default=timezone.now)
    endTime = models.DateTimeField(null=True, blank=True, default=get100Years)
    timeZone = models.CharField(max_length=128, blank=False)
    notes = models.CharField(max_length=512, blank=True, null=True)


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

class HasDownloadableFiles(object):
    """ Mixin to support models that have downloadable files """

    def getDownloadableFiles(self):
        pass


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
            try:
                for part in column.split('.'):
                    obj = getattr(self, part)
                text = obj
            except:
                #TODO: look at datatables select.  We are doing this here to bypass the checkbox problem but it will swallow other errors
                pass
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
        if columns[0] == 'checkbox':
            columns = columns[1:]  # ignore the checkbox column
        values = self.toMapList(columns)
        result = dict(zip(columns, values))
        return result

    @property
    def app_label(self):
        return self._meta.app_label

    @classmethod
    def cls_type(cls):
        # IMPORTANT -- override this if it is not the registered model name in site settings JS_MAP
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
        return reverse('search_map_single_object', kwargs={'modelPK': self.pk,
                                                           'modelName': self.type})

    @property
    def lat(self):
        """ latitude """
        position = self.getPosition()
        if position:
            return position.latitude

    @property
    def lon(self):
        """ longitude """
        position = self.getPosition()
        if position:
            return position.longitude

    @property
    def alt(self):
        """ altitude """
        try:
            position = self.getPosition()
            if position:
                return position.altitude
        except:
            pass
        return None

    @property
    def head(self):
        """ heading """
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
    def buildNoteQuery(cls, search_keywords, model_class=None):
        """
        Build a query that will search for a note that contains the keyword for notes that point to the object type of this class
        :param search_keywords: keywords to search for in the format keyword and keyword or keyword etc
        :return: the found list of pks
        """

        if model_class:
            master_query = LazyGetModelByName(settings.XGDS_NOTES_NOTE_MODEL).get().objects.filter(content_type__app_label=model_class._meta.app_label,
                                                                                                   content_type__model=model_class._meta.model_name)
        else:
            master_query = LazyGetModelByName(settings.XGDS_NOTES_NOTE_MODEL).get().objects.all()

        counter = 0
        last_query = None
        keyword_query = None
        while counter < len(search_keywords):
            if counter % 2 == 0:
                last_query = Q(**{'content__icontains': search_keywords[counter]})
            else:
                if not keyword_query:
                    keyword_query = last_query
                else:
                    join_type = search_keywords[counter]
                    if join_type == 'and':
                        keyword_query &= last_query
                    else:
                        keyword_query |= last_query
            counter += 1
        if not keyword_query:
            keyword_query = last_query

        result = master_query.filter(keyword_query)
        object_ids = result.values_list('object_id', flat=True)

        return list(object_ids)


    def to_kml(self, id, name, description, lat, lon):
        alt = 0.0
        ns = '{http://www.opengis.net/kml/2.2}'
        # kmlStyles = []
        # innerIconStyle = styles.IconStyle(id="blueStyle", color="#4286f4")
        # iconStyle = styles.Style(ns=ns, id="blueIcon", styles=[innerIconStyle])
        # kmlStyles.append(iconStyle)

        placemark = kml.Placemark(ns, id, name, description)
        placemark.geometry = Point([(lon, lat, alt)])

        return placemark

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
    is_update = models.BooleanField(default=False)
    hostname = models.CharField(max_length=32, default=settings.HOSTNAME)

    def getSerializedData(self):
        result = {'object_id': self.object_id,
                  'content_type_app_label': self.content_type.app_label,
                  'content_type_model': self.content_type.model,
                  'url': self.url,
                  'serialized_form': self.serialized_form,
                  'is_update': self.is_update}
        return result

    def toRelayJson(self):
        result = {'relay_event_pk': self.pk}
        return json.dumps(result)

    def __unicode__(self):
        return "%d: %s" % (self.pk, self.url)


class RelayFile(models.Model):
    file_to_send = models.FileField(upload_to=getRelayFileName, max_length=256)
    file_key = models.CharField(max_length=64)
    relay_event = models.ForeignKey(RelayEvent)


CONDITION_HISTORY_MODEL = LazyGetModelByName(settings.XGDS_CORE_CONDITION_HISTORY_MODEL)


class AbstractCondition(models.Model):
    source = models.CharField(null=False, blank=False, max_length=64,
                              db_index=True)  # where did this condition originate
    source_id = models.CharField(null=True, blank=True, max_length=64,
                                 db_index=True)  # id from the source side so we can correlate or update conditions
    xgds_id = models.CharField(null=True, blank=True, max_length=64,
                               db_index=True)  # id on the xGDS side in case we want to map this condition to something
    timezone = models.CharField(null=True, blank=False, max_length=32, default=settings.TIME_ZONE,
                                db_index=True)  # timezone of the condition (for display)
    start_time = models.DateTimeField(editable=False, null=True, blank=True,
                                      db_index=True)  # if the condition has a duration, what is its start time
    end_time = models.DateTimeField(editable=False, null=True, blank=True,
                                    db_index=True)  # if the condition has a duration, what is its end time
    name = models.CharField(null=True, blank=True, max_length=64)  # name which probably came from the source

    class Meta:
        abstract = True

    # In User class declaration
    @classmethod
    def create(cls, condition_source, condition_source_id):
        return cls(source=condition_source,
                   source_id=condition_source_id)

    def populate(self, source_time, condition_data):
        """ Fill in condition data and create a new condition history """
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

        # create relevant condition history
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

    def getRedisSSEChannel(self):
        return 'condition'

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
        history_name = settings.XGDS_CORE_CONDITION_HISTORY_MODEL.replace('.', '_')
        return getattr(self, history_name)


class Condition(AbstractCondition):
    pass


DEFAULT_CONDITION_FIELD = lambda: models.ForeignKey('xgds_core.Condition', null=True, blank=True)


class AbstractConditionHistory(models.Model):
    condition = 'set to DEFAULT_CONDITION_FIELD() or similar in derived classes'
    source_time = models.DateTimeField(editable=False, null=False, blank=False, db_index=True,
                                       default=timezone.now)  # actual source time of the condition
    creation_time = models.DateTimeField(editable=False, null=False, blank=False, db_index=True,
                                         default=timezone.now)  # when was this modified in xGDS
    status = models.CharField(null=True, blank=True,
                              max_length=128)  # id on the xGDS side in case we want to map this condition to something
    jsonData = ExtrasDotField(null=True, blank=True)  # dot dictionary to hold the raw data and any extra data

    def toJson(self):
        return serialize('json', [self.condition, self], use_natural_foreign_keys=True)

    def populate(self, condition_data_dict, save=True):
        if save:
            self.save()

    def broadcast(self):
        # By the time you call this you know that this instance has been newly inserted into the database and needs to broadcast itself
        try:
            json_condition_history = self.toJson()
            result = {'status': 'success',
                      'data': json_condition_history}
            json_string = json.dumps(result, cls=DatetimeJsonEncoder)
            if settings.XGDS_SSE and settings.XGDS_CORE_REDIS:
                publishRedisSSE(self.getBroadcastChannel(), self.getSseType(), json_string)
                callRemoteRebroadcast(self.getBroadcastChannel(), self.getSseType(), json_string)
                return json_string
            else:
                return json_string

        except:
            traceback.print_exc()
            # TODO: discuss what to do with failures here
            result = {'status': 'failure'}
            json_string = json.dumps(result, cls=DatetimeJsonEncoder)
            return json_string

    class Meta:
        abstract = True
        ordering = ['creation_time']


class ConditionHistory(AbstractConditionHistory):
    condition = DEFAULT_CONDITION_FIELD()


class NameManager(models.Manager):

    def get_by_natural_key(self, name):
        return self.get(name=name)


# NOTE! This is a special model that is matched to the schema of MySQL's
# information_schema DB global_variables table. That table must be mapped
# into this application's database using a MySQL view declaration.
# create view xgds_basalt.global_variables as select * from information_schema.global_variables;

class DbServerInfo(models.Model):
    @classmethod
    def getServerId(cls):
        return int(cls.objects.get(variableName='SERVER_ID').variableValue)

    @classmethod
    def getAutoIncrementOffset(cls):
        return int(cls.objects.get(variableName='AUTO_INCREMENT_OFFSET').variableValue)

    @classmethod
    def getAutoIncrementIncrement(cls):
        return int(cls.objects.get(variableName='AUTO_INCREMENT_INCREMENT').variableValue)

    # Method returns True if the given pk was generated by a different server
    # we assume (hack-ish-ly) that our auto_increment_increment is 10 and
    # check only the last digit of the key we are given.
    @classmethod
    def keyFromExternalServer(cls, pk):
        myPkOffset = cls.getAutoIncrementOffset()
        myPkIncrement = cls.getAutoIncrementIncrement()
        return (myPkIncrement != 1) and ((pk % myPkIncrement) != myPkOffset)

    variableName = models.CharField(max_length=64, primary_key=True, db_column='VARIABLE_NAME')
    variableValue = models.IntegerField(null=True, blank=True, db_column='VARIABLE_VALUE')

    class Meta:
        db_table = 'global_variables'
        managed = False


class BroadcastMixin(object):

    def getBroadcastChannel(self):
        return 'sse'

    def getSseType(self):
        return self.__class__.cls_type().lower()

    def broadcast(self):
        # By the time you call this you know that this instance has been newly inserted into the database and needs to broadcast itself
        try:
            result = self.toMapDict()
            json_string = json.dumps(result, cls=DatetimeJsonEncoder)
            if settings.XGDS_CORE_REDIS and settings.XGDS_SSE:
                publishRedisSSE(self.getBroadcastChannel(), self.getSseType(), json_string)
                callRemoteRebroadcast(self.getBroadcastChannel(), self.getSseType(), json_string)
            return result
        except:
            traceback.print_exc()


class State(models.Model):
    """
    Stores the state as a json blob.  In general, this can be used to record state information
    in a flexible way.  It is also used to store the most current state, for appending to models
    during an import (for example, to get whatever extra metadata needs to be stored with those models, such as
    flight or vehicle).
    """
    start = models.DateTimeField(db_index=True)
    end = models.DateTimeField(db_index=True, null=True, blank=True)
    active = models.BooleanField(default=False)
    dateModified = models.DateTimeField(db_index=True)
    key = models.CharField(max_length=32, db_index=True, unique=True)
    notes = models.CharField(max_length=256, null=True, blank=True)
    values = ExtrasDotField(default='')  # a dictionary of name/value pairs that get added for import

    def __unicode__(self):
        return u'%s' % (self.key)

    class Meta:
        ordering = ['start']


class AbstractVehicle(models.Model):
    objects = NameManager()

    name = models.CharField(max_length=64, blank=True, db_index=True, unique=True)
    notes = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=16, db_index=True)
    extras = ExtrasDotField(default='')
    # to be used for 'primary vehicles' which show up in the import dropdown
    primary = models.NullBooleanField(null=True, default=False)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name

    def getDict(self):
        return {"name": self.name, "notes": self.notes, "type": self.type}

    def natural_key(self):
        return (self.name)
    
    @classmethod
    def get_vehicles_for_dropdown(cls):
        """ Exclude DefaultVehicle if it is not the only one"""
        vehicles = LazyGetModelByName(settings.XGDS_CORE_VEHICLE_MODEL).get().objects.all()
        if vehicles.count() > 1:
            vehicles = vehicles.exclude(type='GenericVehicle')
        return vehicles


class Vehicle(AbstractVehicle):
    pass


# TODO if you are not using the default flights or vehicles or group flights you will have to override these in your classes
DEFAULT_FLIGHT_FIELD = lambda: models.ForeignKey('xgds_core.Flight', null=True, blank=True)
DEFAULT_VEHICLE_FIELD = lambda: models.ForeignKey(Vehicle, null=True, blank=True)
DEFAULT_GROUP_FLIGHT_FIELD = lambda: models.ForeignKey('xgds_core.GroupFlight', null=True, blank=True)


class HasVehicle(object):
    vehicle = "TODO SET TO DEFAULT_VEHICLE_FIELD or similar"

    @property
    def vehicle_name(self):
        if self.vehicle:
            return self.vehicle.name
        return ''


class IsTreeChild(object):
    """
    Interface for providing a child block of json for fancytree
    """

    @classmethod
    def get_tree_json(cls, parent_class, parent_pk):
        """
        Get a list of json blocks for the tree based on the parent class and pk.
        Sample json:
        [{"title": settings.GEOCAM_TRACK_TRACK_MONIKER,
                             "selected": False,
                             "tooltip": "Tracks for " + self.name,
                             "key": self.uuid + "_tracks",
                             "data": {
                                 "json": reverse('geocamTrack_mapJsonTrack', kwargs={'uuid': str(self.track.uuid)}),
                                 "kmlFile": reverse('geocamTrack_trackKml', kwargs={'trackName': self.track.name}),
                                 "sseUrl": "",
                                 "type": 'MapLink',
                             }
                             }]
        :param parent_class: the package & class name
        :param parent_pk: the pk of the parent
        :return: a list of valid json block for the tree, or None
        """
        # TODO subclass should implement this
        return None


class IsFlightChild(IsTreeChild):
    """
    Interface specifically for providing children to a flight for the tree (fancytree)
    """
    pass


class IsFlightData(object):
    """
    Interface to provide name and link to search results / viewing page for searchable data that is part of a flight
    """

    @classmethod
    def get_info_json(cls, flight_pk):
        """
        Implement this in derived classes
        Return a block of json that has
        { name: renderable name, ie Notes,
          count: number of items, ie 10,
          url: link to open the items }
        :param flight_pk: the pk of the containing flight
        :return: json, or none
        """
        return None


class AbstractFlight(UuidModel, HasVehicle):
    objects = NameManager()

    name = models.CharField(max_length=128, blank=True, unique=True,
                            help_text='it is episode name + asset role. i.e. 20130925A_ROV', db_index=True)
    vehicle = DEFAULT_VEHICLE_FIELD()
    locked = models.BooleanField(blank=True, default=False)
    start_time = models.DateTimeField(null=True, blank=True, db_index=True)
    end_time = models.DateTimeField(null=True, blank=True, db_index=True)
    timezone = models.CharField(null=True, blank=False, max_length=128, default=settings.TIME_ZONE)
    notes = models.TextField(blank=True, null=True)
    group = 'set to DEFAULT_GROUP_FLIGHT_FIELD() or similar in derived classes'

    # if this was from a file import, include information about the source
    source_root = models.CharField(null=True, blank=True, max_length=512)

    def natural_key(self):
        return (self.name)

    @classmethod
    def cls_type(cls):
        return 'Flight'

    def hasStarted(self):
        return (self.start_time != None)

    def hasEnded(self):
        if self.hasStarted():
            return (self.end_time != None)
        return False

    def startFlightExtras(self, request):
        pass

    def stopFlightExtras(self, request):
        pass

    def thumbnail_time_url(self, event_time):
        return self.thumbnail_url()

    def thumbnail_url(self):
        return ''

    def view_time_url(self, event_time):
        return self.view_url()

    def view_url(self):
        return ''

    def __unicode__(self):
        return self.name

    def update_start_time(self, start):
        """
        Update the start time and save
        :param start: the start time
        """
        if not self.start_time or start < self.start_time:
            self.start_time = start
            self.save()

    def getTreeJsonChildren(self):
        children = []
        if hasattr(self, 'track'):
            children.append({"title": settings.GEOCAM_TRACK_TRACK_MONIKER,
                             "selected": False,
                             "tooltip": "Tracks for " + self.name,
                             "key": self.uuid + "_tracks",
                             "data": {
                                 "json": reverse('geocamTrack_mapJsonTrack', kwargs={'uuid': str(self.track.uuid)}),
                                 "kmlFile": reverse('geocamTrack_trackKml', kwargs={'trackName': self.track.name}),
                                 "sseUrl": "",
                                 "type": 'MapLink',
                             }
                             })
        if self.plans:
            myplan = self.plans[0].plan
            children.append({"title": settings.XGDS_PLANNER_PLAN_MONIKER,
                             "selected": False,
                             "tooltip": "Plan for " + self.name,
                             "key": self.uuid + "_plan",
                             "data": {"json": reverse('planner2_mapJsonPlan', kwargs={'uuid': str(myplan.uuid)}),
                                      "kmlFile": reverse('planner2_planExport', kwargs={'uuid': str(myplan.uuid),
                                                                                        'name': myplan.name + '.kml'}),
                                      "sseUrl": "",
                                      "type": 'MapLink',
                                      }
                             })

        for the_class in IsFlightChild.__subclasses__():
            tree_jsons = the_class.get_tree_json(settings.XGDS_CORE_FLIGHT_MODEL, self.pk)
            if tree_jsons:
                children.extend(tree_jsons)

        return children

    def getTreeJson(self):
        result = {"title": self.name,
                  "lazy": True,
                  "key": self.uuid,
                  "tooltip": self.notes,
                  "folder": True,
                  "data": {"type": self.__class__.__name__,
                           "vehicle": self.vehicle.name,
                           "href": '',  # TODO add url to the flight summary page when it exists
                           "childNodesUrl": reverse('xgds_core_flightTreeNodes', kwargs={'flight_id': self.id})
                           }
                  # "children": self.getTreeJsonChildren()
                  }

        return result

    def get_info_jsons(self):
        """
        Get all the flight data json descriptive blocks
        :return: a list of json blocks
        """
        result = []
        for the_class in IsFlightData.__subclasses__():
            flight_data_json = the_class.get_info_json(self.pk)
            if flight_data_json:
                result.append(flight_data_json)
        return result

    @property
    def plans(self):
        return LazyGetModelByName(settings.XGDS_PLANNER_PLAN_EXECUTION_MODEL).get().objects.filter(flight=self)

    def stopTracking(self):
        if settings.PYRAPTORD_SERVICE is True:
            pyraptord = getPyraptordClient()
            serviceName = self.vehicle.name + "TrackListener"
            stopPyraptordServiceIfRunning(pyraptord, serviceName)

        if hasattr(self, 'track'):
            if self.track.currentposition_set:
                try:
                    position = self.track.currentposition_set.first()
                    if position:
                        position.delete()
                except:
                    pass

    def startTracking(self):
        # TODO define
        pass

    class Meta:
        abstract = True
        ordering = ['-name']


class Flight(AbstractFlight):
    group = DEFAULT_GROUP_FLIGHT_FIELD()
    vehicle = DEFAULT_VEHICLE_FIELD()
    summary = models.CharField(max_length=1024, blank=True, null=True)


class HasFlight(object):
    """ Mixin to support models that have flights """
    flight = "TODO SET TO DEFAULT_FLIGHT_FIELD or similar"

    @property
    def vehicle(self):
        if self.flight:
            return self.flight.vehicle
        return None

    @property
    def vehicle_name(self):
        vehicle = self.vehicle
        if vehicle:
            return vehicle.name
        return ''

    @property
    def flight_name(self):
        if self.flight:
            return self.flight.name
        return ''

    @property
    def flight_group_name(self):
        if self.flight:
            return self.flight.group.name
        else:
            return None


DEFAULT_ONE_TO_ONE_FLIGHT_FIELD = lambda: models.OneToOneField(Flight, related_name="active", null=True, blank=True)


class AbstractActiveFlight(models.Model, HasFlight):
    flight = 'set to DEFAULT_ONE_TO_ONE_FLIGHT_FIELD() or similar in derived classes'

    def __unicode__(self):
        return (u'ActiveFlight(%s, %s)' %
                (self.pk, repr(self.flight.name)))

    class Meta:
        abstract = True


class ActiveFlight(AbstractActiveFlight):
    flight = DEFAULT_ONE_TO_ONE_FLIGHT_FIELD()


class AbstractGroupFlight(models.Model):
    """
    This GroupFlight model represents the overall coordinated
    operation.
    """
    objects = NameManager()

    name = models.CharField(max_length=128, blank=True, unique=True,
                            help_text='Usually same as episode name. I.e. 201340925A', db_index=True)
    notes = models.TextField(blank=True, null=True)

    def thumbnail_url(self):
        return ''

    def thumbnail_time_url(self, event_time):
        return self.thumbnail_url()

    def view_time_url(self, event_time):
        return ''  # TODO implement

    def view_url(self):
        return ''  # TODO implement

    def summary_url(self):
        return reverse('xgds_core_group_flight_summary', kwargs={'groupFlightName': self.name})

    @property
    def flights(self):
        # TODO implement
        return None

    def natural_key(self):
        return (self.name)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name


class GroupFlight(AbstractGroupFlight):
    @property
    def flights(self):
        return self.flight_set.all()


class ImportedTelemetryFile(models.Model):
    # The name of the file imported
    filename = models.CharField(max_length=256,blank=False,null=False,db_index=True)
    # Command line used to import
    commandline = models.CharField(max_length=512,blank=False,null=False)
    # When it was imported
    timestamp = models.DateTimeField(blank=False,null=False)
    # How long it took to import
    duration = models.IntegerField(blank=False,null=False,default=0)
    # The return code from running the importer
    returncode = models.IntegerField(blank=False,null=False)
    # The output of the script that imported the file
    runlog = models.TextField()
    errlog = models.TextField()
    # If the import fails and we keep trying keep track of how many times
    retry_count = models.IntegerField()

    def __unicode__(self):
        status = 'success'
        if self.returncode <> 0:
            status = 'failed'
        return '%s @ %s (%s)' % (self.filename, self.timestamp, status)
