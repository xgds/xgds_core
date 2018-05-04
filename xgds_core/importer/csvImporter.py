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

import csv
from collections import OrderedDict

from geocamUtil.loader import getModelByName
from xgds_core.views import getActiveStates, getState
from xgds_core.flightUtils import get_default_vehicle, getFlight, create_group_flight, \
    get_next_available_group_flight_name, lookup_vehicle, lookup_flight
from geocamUtil.loader import LazyGetModelByName
from dateutil.parser import parse as dateparser

from django.conf import settings
from django.utils import timezone

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


def load_yaml(yaml_file, defaults):
    """
    Load the contents of a Yaml file and return it as a dictionary.
    :param yaml_file: the path to the file to load.  If running within django, the path can be /apps/myapp/path/to/yaml
    :param defaults: default dictionary to append to self.config defaults
    :return: the dictionary of data
    """
    the_stream = open(yaml_file, 'r')
    try:
        data = ordered_load(the_stream, Loader=Loader)
        data['fieldnames'] = data['fields'].keys()

        if not defaults:
            defaults = {}
        if 'defaults' not in data:
            data['defaults'] = defaults
        else:
            data['defaults'].update(defaults)

        data['timefields'] = []
        for key, value in data['fields'].iteritems():
            if 'time' in value['type']:
                data['timefields'].append(key)

        if 'flight_required' not in data:
            data['flight_required'] = False

    finally:
        the_stream.close()
    return data


class CsvImporter(object):
    """
    The class to manage specific methods and self.configurations for loading csv files.
    """

    def __init__(self, yaml_file_path, csv_file_path, vehicle_name=None, flight_name=None, defaults=None, force=False, stateKey=None):
        """
        Initialize with a path to a configuration yaml file and a path to a csv file
        :param yaml_file_path: The path to the yaml self.configuration file for import
        :param csv_file_path: The path to the csv file to import
        :param vehicle_name: The name of the vehicle
        :param flight_name: The name of the flight
        :param stateKey: The state key to look up the active state.  None will use the last active state.
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
        self.configure(yaml_file_path, csv_file_path, vehicle_name, flight_name, defaults, force)

    def get_time(self, row):
        """
        Read the timestamp from a row, or use the current time
        :param row:
        :return: the time
        """
        if 'timestamp' in row:  #TODO timezone
            the_time = dateparser(row['timestamp'])
        else:
            the_time = timezone.now()
        return the_time

    def get_or_create_flight(self, row):
        """
        Use the timestamp in the row to look up or create a flight, which is stored in self.flight.
        :param row: the first row of the csv
        """
        self.start_time = self.get_time(row)
        self.flight = getFlight(self.start_time, self.vehicle)
        if not self.flight:
            # There was not a valid flight, so let's make a new one.  We will make a new group flight.
            group_flight = create_group_flight(get_next_available_group_flight_name(the_time.strftime('%Y%m%d')))
            if group_flight:
                flights = group_flight.flights.filter(vehicle=self.vehicle)
                self.flight = flights[0]  # there should only be one

                # set its start time
                self.flight.start_time = self.start_time
                self.flight.save()
        else:
            self.update_flight_start(self.start_time)

    def open_csv(self, csv_file_path):
        """ Open the CSV file and return a tuple of the file, dictreader"""
        delimiter = ','
        if 'delimiter' in self.config:
            delimiter = self.config['delimiter']

        quotechar = '"'
        if 'quotechar' in self.config:
            quotechar = self.config['quotechar']

        self.csv_file = open(csv_file_path, 'rb')
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
                row[field_name] = dateparser(row[field_name])
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
            if not self.flight.start_time or start < self.flight.start_time:
                self.flight.start_time = start
                self.flight.save()

    def load_csv(self):
        """
        Load the CSV file according to the self.configuration, and store the values in the database using the
        Django ORM and including any data from the current state.
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
        finally:
            self.csv_file.close()
        return new_models

    # def get_state_dict(self, stateKey):
    #     result = {}
    #     state = None
    #     if stateKey:
    #         state = getState(stateKey)
    #     else:
    #         states = getActiveStates()
    #         if states:
    #             state = states.last()
    #     if state:
    #         result = state.values.to_dict()
    #     return result

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

    def configure(self, yaml_file_path, csv_file_path, vehicle_name=None, flight_name=None, defaults=None, force=False):
        """
        self.configure flight, vehicle, the yanl self.configuration file.  Create a flight if necessary based on the first time.
        :param yaml_file_path: The path to the yaml self.configuration file for import
        :param csv_file_path: The path to the csv file to import
        :param vehicle_name: The name of the vehicle
        :param flight_name: The name of the flight
        :param defaults: Optional additional defaults to add to objects
        :return: the self.config, which will contain the vehicle, flight, csv_file and csv_reader
        """
        self.vehicle = lookup_vehicle(vehicle_name)
        self.flight = lookup_flight(flight_name)
        self.config = load_yaml(yaml_file_path, defaults)
        self.open_csv(csv_file_path)
        first_row = self.get_first_row()
        if not force:
            exists = self.check_data_exists(self.config, first_row)
            if exists:
                print " ABORTING: MATCHING DATA FOUND"
                print first_row
                raise Exception('Matching data found, data already imported', first_row)
        if not self.flight and self.config['flight_required']:
            # read the first timestamp and find a flight for it
            self.get_or_create_flight(first_row)
            if self.flight:
                self.config['defaults']['flight_id'] = self.flight.id
        return self.config

    # def do_import(self, yaml_file_path, csv_file_path, vehicle_name=None, flight_name=None, defaults=None, force=False, stateKey=None):
    #
    #
    #     self.config = self.configure(yaml_file_path, csv_file_path, vehicle_name, flight_name, defaults, force)
    #
    #     # state = getStateDict(stateKey)
    #     # state.update(defaults)
    #     return self.load_csv()


