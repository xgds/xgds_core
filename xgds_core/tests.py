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

import pydevd
import requests
import datetime
import json
import pytz
from django.conf import settings

from django.test import TestCase


class xgds_coreTest(TestCase):
    """
    Tests for xgds_core
    """
    def test_xgds_core(self):
        pass


class xgds_coreConditionSetTest(TestCase):
    
    def test_set_condition(self):
        pydevd.setttrace('128.102.236.67')
        url = "%s%s" % (settings.HOSTNAME, '/xgds_core/condition/set/')
        isonow = datetime.datetime.now(pytz.utc).isoformat()
        data = {'time': isonow,
                'source': 'xgds_test',
                'id': 'test_one',
                'data': {'start_time': isonow,
                         'status': 'Started',
                         'timezone': settings.TIME_ZONE,
                         'name': 'test_set_condition',
                         'extra': 'Start time should be set',
                         }
                }
        response = requests.post(url, data=data)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'success')
        condition_history_json = json_response['data']
        self.assertEqual(condition_history_json['status'], 'Started')
        self.assertEqual(condition_history_json['extra'], 'Start time should be set')
        self.assertEqual(condition_history_json['source_time'], isonow)
        self.assertEqual(condition_history_json['jsonData'], json.dumps(data['data']))
#         self.assertEqual(condition_history_json['name'], 'test_set_condition')
#         self.assertEqual(condition_history_json['timezone'], settings.TIME_ZONE)
#         self.assertEqual(condition_history_json['start_time'], isonow)
#         self.assertEqual(condition_history_json['id'], 'test_one')
#         self.assertEqual(condition_history_json['source'], 'xgds_test')

class xgds_coreConditionUpdateTest(TestCase):

    def test_update_condition(self):
        url = "%s%s" % (settings.HOSTNAME, '/xgds_core/condition/set/')
        isonow = datetime.datetime.now(pytz.utc).isoformat()
        data = {'time': isonow,
                'source': 'xgds_test',
                'id': 'test_one',
                'data': {'end_time': isonow,
                         'status': 'Ended',
                         'extra': 'End time should be set',
                         }
                }
        response = requests.post(url, data=data)
        
        