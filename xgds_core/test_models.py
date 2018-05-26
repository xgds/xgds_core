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

import datetime
import json
import pytz
from django.conf import settings
from django.test import TestCase

from xgds_core.models import *

class xgds_testAllTheModels(TestCase):
    """
    Tests for xgds_core models
    """
    fixtures=['xgds_core_testing.json']

    def test_Constant(self):
        c = Constant()
        c.name = 'pi'
        c.value = '4'
        # test unicode method
        assert('%s'%c == 'pi: 4')

    def test_XgdsUser(self):
        xu = XgdsUser()
        xu.first_name = 'Benedict'
        xu.last_name = 'Cumberbatch'
        # test unicode method
        assert('%s' % xu == 'Benedict Cumberbatch')
        # test db write
        number_of_benedicts = len(XgdsUser.objects.filter(first_name='Benedict'))
        xu.save()
        new_number_of_benedicts = len(XgdsUser.objects.filter(first_name='Benedict'))
        assert(new_number_of_benedicts>number_of_benedicts)

    def test_RelayEvent(self):
        event = RelayEvent()
        event.object_id = 1
        #event.content_object = None
        event.content_type_id = 1
        event.acquisition_time = datetime.datetime.utcnow()
        event.relay_start_time = datetime.datetime.utcnow()
        event.relay_success_time = datetime.datetime.utcnow()
        event.url = 'url://myurl'
        event.is_update = True
        event.hostname = 'host'
        event.save()

        esd = event.getSerializedData()
        assert(esd['object_id']==esd.object_id)
        assert(esd['content_type_app_label']==esd.content_type_app_label)
        assert(esd['content_type_label']==esd.content_type_label)
        assert(esd['content_type_id']==1)
        assert(esd['url']==esd.url)
        assert(esd['serialized_form']==esd.serialized_form)
        assert(esd['is_update']==esd.is_update)

        erj_str = event.toRelayJson()
        erj = json.loads(erj_str)
        assert(erj is not None)

        name = '%s' % event
        # what should it be?
        assert(name is not None)


    def test_HasFlight(self):
        # there is one ActiveFlight in the test fixture
        af = ActiveFlight.objects.filter(id=1)[0]
        assert('%s'%af=="ActiveFlight(1, u'Christmas in a Generic Vehicle')")
        assert(af.vehicle is not None)
        assert(af.vehicle_name is not None)
        assert(af.flight_name is not None)
        assert(af.flight_group_name is not None)


    def test_Condition(self):
        condition = Condition.create('test_source','test_source_id')
        assert(condition is not None)
