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

import os
import pytz
import datetime
from django.conf import settings
from django.test import TransactionTestCase
from xgds_core.importer.csvImporter import CsvImporter


class test_csv(TransactionTestCase):
    """
    Tests for csv importer
    """
    fixtures = ['xgds_core_testing.json']
    
    def test_parse(self):
        import os
        yamlfile = os.path.join(os.path.dirname(__file__),'test_files/csv.yaml')
        csvfile = os.path.join(os.path.dirname(__file__),'test_files/data.csv')
        vehicle = 'Generic Vehicle'
        flight = 'Christmast in a Generic Vehicle'
        importer = CsvImporter(yamlfile, csvfile, vehicle, flight, replace=True)
        values = importer.load_to_list()

        self.assertEqual(values[0]['timestamp'], datetime.datetime(2019,1,1,1,2,3,456789).replace(tzinfo=pytz.UTC))
        self.assertTrue('myfieldname' not in values[0])
        self.assertEqual(values[0]['truth'], True)
        self.assertEqual(values[0]['heading'], 270)
        self.assertEqual(values[0]['speed'], 3.08)
        self.assertEqual(values[0]['temperature'], -2.0)
        self.assertEqual(values[0]['feelslike'], 28.4)
        self.assertEqual(values[0]['description'], 'cold')

        self.assertEqual(values[1]['timestamp'], datetime.datetime(2019,1,1,1,2,4,567899).replace(tzinfo=pytz.UTC))
        self.assertTrue('myfieldname' not in values[1])
        self.assertEqual(values[1]['truth'], False)
        self.assertEqual(values[1]['heading'], 180)
        self.assertEqual(values[1]['speed'], 4.09)
        self.assertEqual(values[1]['temperature'], 34)
        self.assertEqual(values[1]['feelslike'], 93.2)
        self.assertEqual(values[1]['description'], 'hot')
        
        # default value
        self.assertTrue('flight_id' in values[0])
        self.assertTrue('flight_id' in values[1])
        
        # remove the keys there should be
        for k in ['timestamp','truth','heading','speed','temperature','feelslike','description','flight_id']:
            for v in values:
                self.assertTrue(k in v)
                del v[k]

        # and there should be nothing left
        self.assertEqual(len(values[0].keys()), 0)
        self.assertEqual(len(values[1].keys()), 0)
