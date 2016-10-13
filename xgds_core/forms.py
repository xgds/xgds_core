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
from django.forms.models import ModelChoiceField, ModelForm
from django.forms import BooleanField, CharField, IntegerField, FloatField, DecimalField, ChoiceField, DateTimeField
from xgds_core.models import NamedURL
from django.db.models.fields import *
from django.db.models import Q

# class NamedURLForm(ModelForm):
# 
#     class Meta: 
#         model = NamedURL

class SearchForm(ModelForm):
    queries = None
    
    def addQuery(self, query):
        if query:
            if self.queries:
                self.queries &= query
            else:
                self.queries = query
    
    def buildQueryForCharField(self, fieldname, field, value):
        return Q(**{fieldname+'__icontains':value})

    def buildQueryForBooleanField(self, fieldname, field, value):
        return Q(**{fieldname:value})
    
    def buildQueryForChoiceField(self, fieldname, field, value):
        return Q(**{fieldname:value})
    
    def buildQueryForModelChoiceField(self, fieldname, field, value):
        return Q(**{fieldname+'__id': value.pk})

    def buildQueryForDateTimeField(self, fieldname, field, value, minimum=False, maximum=False):
        if minimum:
            return Q(**{fieldname+'__gte': value})
        elif maximum:
            return Q(**{fieldname+'__lte': value})
        #TODO handle close to date
        return Q(**{fieldname+'=' +value})

    def buildQueryForNumberField(self, fieldname, field, value, minimum=False, maximum=False):
        if minimum:
            return Q(**{fieldname+'__gte': value})
        elif maximum:
            return Q(**{fieldname+'__lte': value})
        return Q(**{fieldname+'__exact': value})

    def buildQueryForField(self, fieldname, field, value, minimum=False, maximum=False):
        field_typename = type(field).__name__
        try:
            if field_typename == 'CharField':
                return self.buildQueryForCharField(fieldname, field, value)
            elif field_typename == 'BooleanField':
                return self.buildQueryForBooleanField(fieldname, field, value)
            elif field_typename == 'ChoiceField':
                return self.buildQueryForChoiceField(fieldname, field, value)
            elif field_typename == 'ModelChoiceField':
                return self.buildQueryForModelChoiceField(fieldname, field, value)
            elif field_typename == 'DateTimeField':
                return self.buildQueryForDateTimeField(fieldname, field, value, minimum=minimum, maximim=maximum)
            elif field_typename == 'DecimalField' or field_typename == 'FloatField' or field_typename == 'IntegerField':
                return self.buildQueryForNumberField(fieldname, field, value, minimum=minimum, maximim=maximum)
            return None
        except:
            traceback.print_exc()
            return None
    
    def getQueries(self):
        #iterate through all of your non-empty fields and build query for them
        # and them together
        self.queries = None
        for key in self.changed_data:
            value = self.cleaned_data[key]
            fieldname = str(key)
            minimum = fieldname.startswith('min_')
            maximum = fieldname.startswith('max_')
            if minimum or maximum:
                fieldname = fieldname[4:]
            try:
                field = self.fields[fieldname]
                builtQuery = self.buildQueryForField(fieldname, field, value, minimum, maximum)
                self.addQuery(builtQuery)
            except:
                pass
        return self.queries
            
    class Meta: 
        abstract = True
