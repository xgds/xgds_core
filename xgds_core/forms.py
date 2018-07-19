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
import pytz
import traceback

from django.forms.models import ModelChoiceField, ModelForm
from django.conf import settings
from django.utils import timezone

from django import forms

from dal import autocomplete

from xgds_core.models import NamedURL
from django.db.models.fields import *
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from geocamUtil import TimeUtil
from geocamUtil.loader import LazyGetModelByName
from geocamUtil.forms.AbstractImportForm import AbstractImportForm


# class NamedURLForm(ModelForm):
# 
#     class Meta: 
#         model = NamedURL

VEHICLE_MODEL = LazyGetModelByName(settings.XGDS_CORE_VEHICLE_MODEL)
GROUP_FLIGHT_MODEL = LazyGetModelByName(settings.XGDS_CORE_GROUP_FLIGHT_MODEL)


class AbstractVehicleForm(forms.Form):
    vehicle = ModelChoiceField(required=False, queryset=VEHICLE_MODEL.get().get_vehicles_for_dropdown(),
                               label=settings.XGDS_CORE_VEHICLE_MONIKER)

    def getVehicle(self):
        if self.cleaned_data['vehicle']:
            return self.cleaned_data['vehicle']
        else:
            return None

    class Meta:
        abstract = True


class AbstractPrimaryVehicleForm(AbstractVehicleForm):
    vehicle = ModelChoiceField(required=False, queryset=VEHICLE_MODEL.get().get_vehicles_for_dropdown().filter(primary=True),
                               label=settings.XGDS_CORE_VEHICLE_MONIKER)

    class Meta:
        abstract = True


class AbstractImportVehicleForm(AbstractImportForm, AbstractPrimaryVehicleForm):

    class Meta:
        abstract = True


class AbstractFlightVehicleForm(forms.Form):
    # TODO We should be able to search on hidden flight id or flight pk but cannot; it does not show up in base fields or cleaned data.
    # flight__id = IntegerField(blank=True)
    # flight__pk = IntegerField(blank=True)

    flight__vehicle = ModelChoiceField(required=False, queryset=VEHICLE_MODEL.get().get_vehicles_for_dropdown(),
                                       label=settings.XGDS_CORE_VEHICLE_MONIKER)

    flight__group = forms.ModelChoiceField(required=False,
                                           queryset=GROUP_FLIGHT_MODEL.get().objects.all(),
                                           label=settings.XGDS_CORE_FLIGHT_MONIKER)
                                           # widget=autocomplete.ModelSelect2(
                                           #     url='/xgds_core/complete/basaltApp.BasaltGroupFlight.json/'))

    def getVehicle(self):
        if self.cleaned_data['flight__vehicle']:
            return self.cleaned_data['flight__vehicle']
        else:
            return None

    class Meta:
        abstract = True
        # widgets = {
        #     'flight__pk': forms.HiddenInput(),
        #     'flight__id': forms.HiddenInput(),
        # }


class SearchForm(ModelForm, AbstractFlightVehicleForm):

    queries = None

    def addQuery(self, query):
        if query:
            if self.queries:
                self.queries &= query
            else:
                self.queries = query
    
    def buildContainsQuery(self, fieldname, field, value):
        return Q(**{fieldname+'__icontains':str(value)})

    def buildQueryForHiddenField(self, fieldname, field, value):
        return Q(**{fieldname: value})

    def buildQueryForCharField(self, fieldname, field, value):
        return Q(**{fieldname+'__icontains':value})

    def buildQueryForBooleanField(self, fieldname, field, value):
        return Q(**{fieldname: value})
    
    def buildQueryForChoiceField(self, fieldname, field, value):
        return Q(**{fieldname: value})
    
    def buildQueryForModelChoiceField(self, fieldname, field, value):
        return Q(**{fieldname+'__id': value.pk})

    def buildQueryForDateTimeField(self, fieldname, field, value, minimum=False, maximum=False):
        if minimum:
            return Q(**{fieldname+'__gte': value})
        elif maximum:
            return Q(**{fieldname+'__lt': value})
        #TODO handle close to date
        return Q(**{fieldname+'__exact': value})

    def buildQueryForNumberField(self, fieldname, field, value, minimum=False, maximum=False):
        if minimum:
            return Q(**{fieldname+'__gte': value})
        elif maximum:
            return Q(**{fieldname+'__lte': value})
        return Q(**{fieldname+'__exact': value})

    def buildQueryForField(self, fieldname, field, value, minimum=False, maximum=False):
        field_typename = type(field).__name__
        try:
            if field.widget.is_hidden:
                return self.buildQueryForHiddenField(fieldname, field, value)
            elif field_typename == 'CharField':
                return self.buildQueryForCharField(fieldname, field, value)
            elif field_typename == 'BooleanField':
                return self.buildQueryForBooleanField(fieldname, field, value)
            elif field_typename == 'ChoiceField':
                return self.buildQueryForChoiceField(fieldname, field, value)
            elif field_typename == 'ModelChoiceField':
                return self.buildQueryForModelChoiceField(fieldname, field, value)
            elif field_typename == 'DateTimeField':
                return self.buildQueryForDateTimeField(fieldname, field, value, minimum=minimum, maximum=maximum)
            elif field_typename == 'DecimalField' or field_typename == 'FloatField' or field_typename == 'IntegerField':
                return self.buildQueryForNumberField(fieldname, field, value, minimum=minimum, maximum=maximum)
            return None
        except:
            traceback.print_exc()
            return None
    
    def getQueries(self):
        #iterate through all of your non-empty fields and build query for them
        # and them together
        self.queries = None

        for key in self.changed_data:
            try:
                value = self.cleaned_data[key]
                fieldname = str(key)
                minimum = fieldname.startswith('min_')
                maximum = fieldname.startswith('max_')
                field = self.fields[fieldname]
                if minimum or maximum:
                    fieldname = fieldname[4:]
                    
                builtQuery = self.buildQueryForField(fieldname, field, value, minimum, maximum)
                self.addQuery(builtQuery)
            except:
                pass
        return self.queries
    
    # populate the times properly
    def clean_time(self, key, timezone):
        event_time = self.cleaned_data[key]
        if not event_time:
            return None
        else:
            if timezone:
                tz = pytz.timezone(timezone)
                event_time = event_time.replace(tzinfo=tz)
            # if there is no timezone it will already be in the settings' local time.
            event_time = TimeUtil.timeZoneToUtc(event_time)
            return event_time

    class Meta: 
        abstract = True


# form for creating a flight group, flights, and all sorts of other stuff needed for our overly complex system.
class GroupFlightForm(forms.Form):
    year = None
    month = None
    day = None
    date = forms.DateField(required=True)
    prefix = forms.CharField(widget=forms.TextInput(attrs={'size': 4}),
                             label="Prefix",
                             required=True)

    notes = forms.CharField(widget=forms.TextInput(attrs={'size': 128}), label="Notes", required=False,
                            help_text='Optional')

    def __init__(self, *args, **kwargs):
        super(GroupFlightForm, self).__init__(*args, **kwargs)
        self.fields['vehicles'] = self.initializeVehicleChoices()
        today = timezone.localtime(timezone.now()).date()

        self.year = today.year
        self.month = today.month - 1
        self.day = today.day
        self.initializeLetter(today.strftime('%Y%m%d'))

    # get the latest GroupFlight, and increment the prefix
    def initializeLetter(self, dateprefix):
        GROUP_FLIGHT_MODEL = LazyGetModelByName(settings.XGDS_CORE_GROUP_FLIGHT_MODEL)
        try:
            last = GROUP_FLIGHT_MODEL.get().objects.filter(name__startswith=dateprefix).order_by('name').last()
            self.fields['prefix'].initial = chr(ord(last.name[-1]) + 1)
        except:
            self.fields['prefix'].initial = 'A'

    def initialize(self, timeinfo):
        self.year = timeinfo['year']
        self.month = timeinfo['month']
        self.day = timeinfo['day']
        self.date = datetime.date(int(self.year), int(self.month), int(self.day))
        self.month = int(timeinfo['month']) - 1  # apparently 0 is january

    def initializeVehicleChoices(self):
        CHOICES = []
        VEHICLE_MODEL = LazyGetModelByName(settings.XGDS_CORE_VEHICLE_MODEL)
        if (VEHICLE_MODEL.get().objects.count() > 0):
            for vehicle in VEHICLE_MODEL.get().objects.all().order_by('name'):
                CHOICES.append((vehicle.name, vehicle.name))

        if len(CHOICES) == 1:
            initial = [c[0] for c in CHOICES]
        else:
            initial = None
        result = forms.MultipleChoiceField(choices=CHOICES, widget=forms.CheckboxSelectMultiple(attrs={"checked": ""}),
                                           required=False, initial=initial)
        return result

