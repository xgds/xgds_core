#__BEGIN_LICENSE__
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
#__END_LICENSE__
import json
from django.contrib.auth.models import User
from django.utils.decorators import classonlymethod
from django.http.response import HttpResponse
from django.views.generic.list import BaseListView
from dal.autocomplete import Select2QuerySetView
from geocamUtil.loader import getModelByName, getClassByName
from django.db.models import Q

def getTypeaheadDictList(objectList):
    ''' Pass in a list of objects and get back a list 
    of dictionaries with pk and str of that object
    '''
    objectDicts = [{'id':obj.pk,
                  'name': str(obj)}
                   for obj in objectList]
    return objectDicts
    
    
def dumpTypeaheadJson(dictList):
    ''' Pass in a list of dictionaries of values you want in your typeahead array
    This will return a clean json string for typeahead.
    '''
    return json.dumps(dictList, separators=(', ',': ')).replace("},","},\n").replace("}]","}\n]")

def getTypeaheadJson(request, model_name):
    ''' pass in the full model name and get the typeahead json array for it
    '''
    model = getModelByName(model_name)
    objects = model.objects.all()
    objectDicts = getTypeaheadDictList(objects)
    return HttpResponse(dumpTypeaheadJson(objectDicts), content_type="application/json")

def getUsersArray():
    regular_users = User.objects.filter(is_superuser=False).exclude(first_name='')
    userDicts = [{'id':user.pk,
                  'name': user.first_name + ' ' + user.last_name}
                 for user in regular_users]
    return dumpTypeaheadJson(userDicts)

def getTypeaheadUsers(request):
    json_users = getUsersArray()
    return HttpResponse(json_users, content_type="application/json")


class XSelect2QuerySetView(Select2QuerySetView):
    # to hold the Q queries
    queries = None
    
    def addQuery(self, query):
        if self.queries:
            self.queries |= query
        else:
            self.queries = query

    def get_queryset(self):
        """Filter the queryset with GET['q']."""
        qs = BaseListView.get_queryset(self)
        if self.q:
            try:
                for key in self.model.getAutocompleteFields():
                    self.addQuery(Q(**{key+'__icontains':self.q}))
                qs = qs.filter(self.queries)
            except:
                try:
                    qs = qs.filter(name__icontains=self.q)
                except:
                    try:
                        qs = qs.filter(shortName__icontains=self.q)
                    except:
                        print 'NO CLUE WHAT FIELDS FOR AUTOCOMPLETE FOR ' + str(self.model)
                        print 'PLEASE ADD classmethod getAutocompleteFields FOR ' + str(self.model)
                        pass

        return qs
    
def getSelectJson2(request, model_name):
    model = getModelByName(model_name)
    return  XSelect2QuerySetView.as_view(model=model)(request)
