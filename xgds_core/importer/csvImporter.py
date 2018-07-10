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

"""
Utilities for loading a csv file into the database per the yaml specification.
see ../../docs/dataImportYml.rst
"""
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

import pytz
import csv
import datetime
from collections import OrderedDict

from geocamUtil.loader import getModelByName
from xgds_core.flightUtils import get_default_vehicle, getFlight, create_group_flight, \
    get_next_available_group_flight_name, lookup_vehicle, lookup_flight, get_or_create_flight
from geocamUtil.loader import LazyGetModelByName
from dateutil.parser import parse as dateparser

from django.conf import settings

VEHICLE_MODEL = LazyGetModelByName(settings.XGDS_CORE_VEHICLE_MODEL)
FLIGHT_MODEL = LazyGetModelByName(settings.XGDS_CORE_FLIGHT_MODEL)


def ordered_load(stream, Loader=Loader, object_pairs_hook=OrderedDict):
    """
    Create an ordered load function for yaml, to keep the dictionary keys in order.
    :param stream:
    :param Loader:
    :param object_pairs_hook:
    :return:
    """

    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)

    return yaml.load(stream, OrderedLoader)


def load_yaml(yaml_file_path, defaults={}):
    """
    Load the contents of a Yaml file and return it as a dictionary.
    :param yaml_file_path: the path to the file to load.
    If running within django, the path can be /apps/myapp/path/to/yaml
    :param defaults: default dictionary to append to self.config defaults
    :return: the dictionary of data
    """
    the_stream = open(yaml_file_path, 'r')
    try:
        data = ordered_load(the_stream, Loader=Loader)
        if not defaults:
            defaults = {}
        if 'defaults' not in data:
            data['defaults'] = defaults
        else:
            data['defaults'].update(defaults)
    finally:
        the_stream.close()
    return data


class CsvImporter(object):
    """
    The class to manage specific methods and self.configurations for loading csv files.
    """

    def __init__(self, yaml_file_path, csv_file_path, vehicle_name=None, flight_name=None, timezone_name='UTC',
                 defaults=None, force=False):
        """
        Initialize with a path to a configuration yaml file and a path to a csv file
        :param yaml_file_path: The path to the yaml self.configuration file for import
        :param csv_file_path: The path to the csv file to import
        :param vehicle_name: The name of the vehicle
        :param flight_name: The name of the flight
        :param timezone_name: The name of the time zone, defaults to UTC
        :param defaults: Optional additional defaults to add to objects
        :return: the imported items
        """
        self.csv_reader = None
        self.csv_file = None
        self.config = None
        self.vehicle = None
        self.flight = None
        self.start_time = None
        self.first_row = None
        self.timezone = self.get_timezone(timezone_name)
        self.configure(yaml_file_path, csv_file_path, vehicle_name, flight_name, defaults, force)

    def load_config(self, yaml_file_path, defaults={}):
        """
        Loads the config file from the yaml path and stores it in self.config
        :param yaml_file_path: the path to the file to load.  If running within django, the path can be /apps/myapp/path/to/yaml
        :param defaults: default dictionary to append to self.config defaults
        """
        self.config = load_yaml(yaml_file_path, defaults)
        self.config['fieldnames'] = self.config['fields'].keys()

        self.config['timefields'] = []
        for key, value in self.config['fields'].iteritems():
            if 'time' in value['type'] or 'iso8601' in value['type']:
                self.config['timefields'].append(key)

        if 'flight_required' not in self.config:
            self.config['flight_required'] = False

    def get_timezone(self, timezone_name=None):
        """
        Builds a pytz timezone to use with times; we store times in utc
        :param timezone_name: the name, defaults to UTC
        :return: the pytz timezone
        """
        if not timezone_name:
            return pytz.utc
        return pytz.timezone(timezone_name)

    def get_time(self, row, field_name='timestamp'):
        """
        Read the timestamp from a row, or use the current time.
        The timezone must be configured first.
        :param row:
        :return: the timezone aware time in utc
        """
        if field_name in row:
            value = row[field_name]
            if not isinstance(value, datetime.datetime):
                time_type = self.config['fields'][field_name]['type']
                if time_type == 'iso8601':
                    the_time = dateparser(row[field_name])
                elif time_type == 'unixtime_float_second':
                    the_time = datetime.datetime.fromtimestamp(float(row[field_name]))
                elif time_type == 'unixtime_int_microsecond':
                    the_time = datetime.datetime.fromtimestamp(int(row[field_name])/1000000)
                else:
                    raise Exception('Unsupported time type %s for row %s' % (time_type, field_name))
            else:
                the_time = value
            if not the_time.tzinfo or the_time.tzinfo.utcoffset(the_time) is None:
                the_time = self.timezone.localize(the_time)
            the_time = the_time.astimezone(pytz.utc)
        else:
            raise Exception('Row is missing a time' + str(row))
        return the_time

    def open_csv(self, csv_file_path):
        """ Open the CSV file and return a tuple of the file, dictreader"""
        delimiter = ','
        if 'delimiter' in self.config:
            delimiter = self.config['delimiter']

        quotechar = '"'
        if 'quotechar' in self.config:
            quotechar = self.config['quotechar']

        self.csv_file = open(csv_file_path, 'rbU')
        try:
            self.csv_reader = csv.DictReader(self.csv_file, fieldnames=self.config['fieldnames'], delimiter=delimiter,
                                             quotechar=quotechar)
        except Exception as e:
            self.csv_file.close()
            raise e

    def update_row(self, row):
        """
        Update the row from the self.config
        :param row: the loaded row
        :return: the updated row, with timestamps and defaults
        """
        if self.config:
            row.update(self.config['defaults'])
            for field_name in self.config['timefields']:
                row[field_name] = self.get_time(row, field_name)
        return row

    def update_flight_end(self, end):
        """
        Update the flight end time AND SAVE THE FLIGHT if it is not set or if this row is after its end time
        :param end: the end time
        :return:
        """
        if self.flight:
            if not self.flight.end_time or end > self.flight.end_time:
                self.flight.end_time = end
                self.flight.save()

    def update_flight_start(self, start):
        """
        Update the flight start time AND SAVE THE FLIGHT if it is not set or if this row is before its start time
        :param start: the start time
        :return:
        """
        if self.flight:
            update_flight_start(self.flight)

    def load_csv(self):
        """
        Load the CSV file according to the self.configuration, and store the values in the database using the
        Django ORM.
        Warning: the model's save method will not be called as we are using bulk_create.
        :return: the newly created models, which may be an empty list
        """

        the_model = getModelByName(self.config['class'])
        new_models = []

        try:
            self.reset_csv()
            for row in self.csv_reader:
                row = self.update_row(row)
                new_models.append(the_model(**row))
            self.update_flight_end(row['timestamp'])
            the_model.objects.bulk_create(new_models)
            self.handle_last_row(row)
        finally:
            self.csv_file.close()
        return new_models

    def handle_last_row(self, row):
        """
        Special processing after the last row
        :param row: the last row
        :return:
        """
        pass

    def check_data_exists(self, row):
        """
        See if there is already identical data
        :param row: typically the first row
        :return: True if it already exists, false otherwise
        """
        row = self.update_row(row)
        the_model = getModelByName(self.config['class'])
        result = the_model.objects.filter(**row)
        return result.exists()

    def reset_csv(self):
        """
        Reset the CSV file for reading from the beginning
        :return:
        """
        if self.csv_file:
            self.csv_file.seek(0)

    def get_first_row(self):
        """
        Get the first row of the csv
        :return: the first row
        """
        if not self.first_row:
            self.first_row = list(self.csv_reader)[0]
            self.reset_csv()
        return self.first_row

    def get_start_time(self):
        """
        Get the start time of this data, as a datetime
        :return: the start time
        """
        if not self.start_time:
            row = self.get_first_row()
            if row and 'timestamp' in row:
                self.start_time = self.get_time(row)
        return self.start_time

    def configure(self, yaml_file_path, csv_file_path, vehicle_name=None, flight_name=None, defaults=None, force=False):
        """
        self.configure flight, vehicle, the yanl self.configuration file.  Create a flight if necessary based on the first time.
        :param yaml_file_path: The path to the yaml self.configuration file for import
        :param csv_file_path: The path to the csv file to import
        :param vehicle_name: The name of the vehicle
        :param flight_name: The name of the flight
        :param timezone_name: The name of the timezone, ie America/Los_Angeles
        :param defaults: Optional additional defaults to add to objects
        :return: the self.config, which will contain the vehicle, flight, csv_file and csv_reader
        """
        self.vehicle = lookup_vehicle(vehicle_name)
        self.flight = lookup_flight(flight_name)
        self.load_config(yaml_file_path, defaults)
        self.open_csv(csv_file_path)
        first_row = self.get_first_row()
        if not force:
            exists = self.check_data_exists(first_row)
            if exists:
                print " ABORTING: MATCHING DATA FOUND"
                # TODO for subsea we will have new rows in existing files so we have to check each row
                print first_row
                raise Exception('Matching data found, data already imported', first_row)
        if not self.flight and self.config['flight_required']:
            # read the first timestamp and find a flight for it
            get_or_create_flight(self.get_start_time(), self.vehicle)
            if self.flight:
                self.config['defaults']['flight_id'] = self.flight.id
        return self.config


