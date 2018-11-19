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

import math
import yaml
import re
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

import pytz
import csv
import datetime
from pydoc import locate
from collections import OrderedDict

from geocamUtil.loader import getModelByName
from xgds_core.flightUtils import get_default_vehicle, getFlight, create_group_flight, \
    get_next_available_group_flight_name, lookup_vehicle, lookup_flight, get_or_create_flight
from geocamUtil.loader import LazyGetModelByName
from geocamTrack.utils import getClosestPosition

from dateutil.parser import parse as dateparser

from django.conf import settings

VEHICLE_MODEL = LazyGetModelByName(settings.XGDS_CORE_VEHICLE_MODEL)
FLIGHT_MODEL = LazyGetModelByName(settings.XGDS_CORE_FLIGHT_MODEL)


def lookup_position(row, timestamp_key='timestamp', position_id_key='position_id', position_found_key=None):
    """ Utility method to help with looking up position"""
    track = None
    if row['flight']:
        track = row['flight'].track
    found_position = getClosestPosition(track=track,
                                        timestamp=row[timestamp_key])

    if found_position:
        row[position_id_key] = found_position.id
        if position_found_key:
            row[position_found_key] = True
    else:
        if position_found_key:
            row[position_found_key] = False
    return row


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
                 defaults=None, force=False, replace=False, skip_bad=False):
        """
        Initialize with a path to a configuration yaml file and a path to a csv file
        :param yaml_file_path: The path to the yaml self.configuration file for import
        :param csv_file_path: The path to the csv file to import
        :param vehicle_name: The name of the vehicle
        :param flight_name: The name of the flight
        :param timezone_name: The name of the time zone, defaults to UTC
        :param defaults: Optional additional defaults to add to objects
        :param force: force load even if data already exists
        :param replace: replace rows instead of creating new ones, matches based on timestamp.
        :param skip_bad: True to skip loading a row if it has bad/unparsable data
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
        self.replace = replace
        self.skip_bad = skip_bad

        # converters, from: to
        self.converters = {'radians': {'degrees': math.degrees},
                           'degrees': {'radians': math.radians}}
        self.configure(yaml_file_path, csv_file_path, vehicle_name, flight_name, defaults, force)

    def load_config(self, yaml_file_path, defaults={}):
        """
        Loads the config file from the yaml path and stores it in self.config
        :param yaml_file_path: the path to the file to load.  Within django, the path can be /apps/myapp/path/to/yaml
        :param defaults: default dictionary to append to self.config defaults
        """
        self.config = load_yaml(yaml_file_path, defaults)
        self.config['fieldnames'] = self.config['fields'].keys()

        self.config['timefields'] = []
        for key, value in self.config['fields'].iteritems():
            if 'skip' not in value or not value['skip']:
                if value['type'] == 'datetime':
                    self.config['timefields'].append(key)
        if self.config['timefields']:
            self.config['timefield_default'] = self.config['timefields'][0]
        else:
            self.config['timefield_default'] = 'timestamp'

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

    def get_time(self, row, field_name=None):
        """
        Read the timestamp from a row, or use the current time.
        The timezone must be configured first.
        :param row: a row dict containing a time to be converted
        :param field_name: key for the value in the row to convert to time
        :return: the timezone aware time in utc
        """
        if not field_name:
            field_name = self.config['timefield_default']
        if field_name not in row:
            raise Exception('Row is missing a time' + str(row))

        value = row[field_name]
        if not isinstance(value, datetime.datetime):
            time_format = self.config['fields'][field_name]['format']
            if time_format == 'iso8601':
                # iso8601 format should include the timezone
                the_time = dateparser(row[field_name])
            elif time_format == 'unixtime_float_second':
                # unix time is always UTC
                the_time = datetime.datetime.utcfromtimestamp(float(row[field_name])).replace(tzinfo=pytz.utc)
            elif time_format == 'unixtime_int_microsecond':
                # unix time is always UTC and we should retain the fractional part
                the_time = datetime.datetime.utcfromtimestamp(int(row[field_name])/1000000.).replace(tzinfo=pytz.utc)
            else:
                # TODO: Should we support general strptime() format strings?
                raise Exception('Unsupported time format %s for row %s' % (time_format, field_name))
        else:
            the_time = value
        if not the_time.tzinfo or the_time.tzinfo.utcoffset(the_time) is None:
            the_time = self.timezone.localize(the_time)
        the_time = the_time.astimezone(pytz.utc)

        return the_time

    def open_csv(self, csv_file_path):
        """ Open the CSV file and return a tuple of the file, dictreader"""
        delimiter = ','
        if 'delimiter' in self.config:
            delimiter = self.config['delimiter']
            if len(delimiter) > 1:
                if 't' in delimiter:
                    delimiter = '\t'

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

    def update_defaults(self, row):
        if 'defaults' in self.config:
            row.update(self.config['defaults'])
        return row

    def delete_skip_fields(self, row):
        for field_name in self.config['fields']:
            field_config = self.config['fields'][field_name]
            if 'skip' in field_config and field_config['skip']:
                # delete entry from row dictionary
                del row[field_name]
        return row

    def parse_regex(self, row):
        for field_name in self.config['fields']:
            field_config = self.config['fields'][field_name]
            if 'skip' in field_config and field_config['skip']:
                continue
            # Extract desired value using defined regex
            if 'regex' in field_config:
                match = re.search(field_config['regex'], row[field_name])
                if match:
                    row[field_name] = match.groups()[-1]
                else:
                    if field_config['required']:
                        raise ValueError('No match for regex %s' % field_config['regex'])
                    else:
                        row[field_name] = None
        return row

    def convert_type(self, row):
        for field_name in self.config['fields']:
            if field_name not in row or not row[field_name]:
                continue
            field_config = self.config['fields'][field_name]
            if 'skip' in field_config and field_config['skip']:
                continue
            # Independent of type, if the value is the string 'None' convert to a python None
            if row[field_name] == 'None':
                row[field_name] = None
                continue
            # If the type is not specified, leave it alone
            if 'type' not in field_config:
                continue
            elif field_config['type'] == 'string' or field_config['type'] == 'text':
                continue
            elif field_config['type'] == 'datetime' or \
                    field_config['type'] == 'date' or \
                    field_config['type'] == 'time':
                try:
                    row[field_name] = self.get_time(row, field_name)
                except ValueError as e:
                    if 'required' in field_config and field_config['required']:
                        raise e
            elif field_config['type'] == 'integer':
                try:
                    row[field_name] = int(row[field_name])
                except ValueError as e:
                    if 'required' in field_config and field_config['required']:
                        raise e
            elif field_config['type'] == 'float':
                try:
                    row[field_name] = float(row[field_name])
                except ValueError as e:
                    if 'required' in field_config and field_config['required']:
                        raise e
            elif field_config['type'] == 'boolean':
                if row[field_name].lower() == 'true':
                    row[field_name] = True
                elif row[field_name].lower() == 'false':
                    row[field_name] = False
                else:
                    row[field_name] = int(row['field_name'])
            elif field_config['type'] == 'nullboolean':
                if row[field_name].lower() == 'true':
                    row[field_name] = True
                elif row[field_name].lower() == 'false':
                    row[field_name] = False
                elif row[field_name].lower() == 'null' or row[field_name].lower() == 'none':
                    row[field_name] = None
                else:
                    row[field_name] = int(row['field_name'])
            elif field_config['type'] == 'key_value':
                if row[field_name] is None:
                    if 'required' in field_config and field_config['required']:
                        raise ValueError(errstr)
                    else:
                        continue
                # split the value into a dictionary
                parts = row[field_name].split(':')
                if len(parts) > 1:
                    row[field_name] = {parts[0]: ':'.join(parts[1:])}
                else:
                    errstr = 'Key value pair not found in %s: %s' % (field_name, str(row))
                    if 'required' in field_config and field_config['required']:
                        raise ValueError(errstr)
            else:
                raise ValueError('%s is not a valid type identifier' % field_config['type'])
        return row

    def convert_units(self, row):
        """
        For any values in the row that have different storage units from units, look for a converter and invoke it
        Also removes any values that are marked skip
        Also processes any regex
        :param row: the row to process
        :return: the row, or None if it had to be skipped
        """
        for field_name in self.config['fields']:
            if field_name not in row or not row[field_name]:
                continue
            field_config = self.config['fields'][field_name]
            if 'skip' in field_config and field_config['skip']:
                continue
            # If storage units are different from provided units, convert values
            if 'storage_units' in field_config and 'units' in field_config:
                storage_units = field_config['storage_units']
                units = field_config['units']
                if units in self.converters:
                    converters = self.converters[units]
                    if storage_units in converters:
                        fcn = locate(field_config['type'])
                        new_value = converters[storage_units](fcn(row[field_name]))
                        row[field_name] = new_value
        return row

    def update_row(self, row):
        """
        Update the row from the self.config
        :param row: the loaded row
        :return: the updated row, with timestamps and defaults
        """
        if self.config:
            # Replace missing fields with default values
            # TODO: resolve what happens or should happen if a value and default are both given
            row = self.update_defaults(row)
            # Delete fields marked skip=True
            row = self.delete_skip_fields(row)
            # Parse any regexes
            row = self.parse_regex(row)
            # Cast strings to the specified types
            row = self.convert_type(row)
            # Convert between provided and desired units
            row = self.convert_units(row)
        return row

    def update_flight_end(self, end):
        """
        Update the flight end time AND SAVE THE FLIGHT if it is not set or if this row is after its end time
        :param end: the end time
        :return:
        """
        if self.flight:
            self.flight.update_end_time(end)

    def update_flight_start(self, start):
        """
        Update the flight start time AND SAVE THE FLIGHT if it is not set or if this row is before its start time
        :param start: the start time
        :return:
        """
        if self.flight:
            self.flight.update_start_time(start)

    def load_csv(self):
        """
        Load the CSV file according to the self.configuration, and store the values in the database using the
        Django ORM.
        Warning: the model's save method will not be called as we are using bulk_create.
        :return: the newly created models, which may be an empty list
        """
        the_model = getModelByName(self.config['class'])
        new_models = []

        rows = self.load_to_list()
        try:
            for row in rows:
                if not self.replace:
                    new_models.append(the_model(**row))
            if row:
                self.update_flight_end(row[self.config['timefield_default']])
            if not self.replace:
                the_model.objects.bulk_create(new_models)
                print 'created %d records' % len(new_models)
            else:
                self.update_stored_data(the_model, rows)
                print 'updated %d records' % len(new_models)
            self.handle_last_row(row)
        except Exception as e:
            print e

        return new_models

    def __iter__(self):
        self.reset_csv()
        return self

    def next(self):
        """
        Loads CSV file entries one at a time
        :return: the next entry as an updated dict
        """
        try:
            row = next(self.csv_reader)
            row = self.update_row(row)
            return row
        except StopIteration:
            self.csv_file.close()
            raise StopIteration

    def load_to_list(self):
        """
        Load the CSV file according to the self.configuration, and store the values in a list of dicts
        :return: a list containing the rows as updated dicts, which may be an empty list
        """
        rows = [r for r in iter(self)]
        return rows

    def update_stored_data(self, the_model, rows):
        """
        # search for matching data based on each row, and update it.
        :param the_model: the model we are working with
        :param rows: the cleaned up rows we are working with
        :return:
        """
        for row in rows:
            filter_dict = {self.config['timefield_default']: row[self.config['timefield_default']]}
            if self.flight:
                filter_dict['flight'] = self.flight
            found = the_model.objects.filter(**filter_dict)
            if found.count() != 1:
                print "ERROR: DID NOT FIND MATCH FOR %s" % str(row[self.config['timefield_default']])
            else:
                item = found[0]
                for key, value in row.iteritems():
                    setattr(item, key, value)
                print 'UPDATED: %s ' % str(item)
                item.save()

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
        if row:
            the_model = getModelByName(self.config['class'])
            result = the_model.objects.filter(**row)
            return result.exists()
        return False

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
            the_list = list(self.csv_reader)
            if the_list:
                self.first_row = the_list[0]
                self.reset_csv()
            else:
                return None

        return self.first_row

    def get_start_time(self):
        """
        Get the start time of this data, as a datetime
        :return: the start time
        """
        if not self.start_time:
            row = self.get_first_row()
            if row and self.config['timefield_default'] in row:
                self.start_time = self.get_time(row)
        return self.start_time

    def configure(self, yaml_file_path, csv_file_path, vehicle_name=None, flight_name=None, defaults=None, force=False):
        """
        self.configure flight, vehicle, yaml configuration file.  Create a flight if necessary based on the first time.
        :param yaml_file_path: The path to the yaml configuration file for import
        :param csv_file_path: The path to the csv file to import
        :param vehicle_name: The name of the vehicle
        :param flight_name: The name of the flight
        :param timezone_name: The name of the timezone, ie America/Los_Angeles
        :param defaults: Optional additional defaults to add to objects
        :param force: force load even if we already have existing data
        :return: the self.config, which will contain the vehicle, flight, csv_file and csv_reader
        """
        self.vehicle = lookup_vehicle(vehicle_name)
        self.flight = lookup_flight(flight_name)

        self.load_config(yaml_file_path, defaults)
        if self.flight:
            # Only set this default value if the model has this attribute
            the_model = getModelByName(self.config['class'])
            if hasattr(the_model,'flight_id'):
                self.config['defaults']['flight_id'] = self.flight.id
            
        self.open_csv(csv_file_path)

        first_row = self.get_first_row()
        if not force and not self.replace and first_row:
            exists = self.check_data_exists(first_row)
            if exists:
                print " ABORTING: MATCHING DATA FOUND"
                # TODO for subsea we will have new rows in existing files so we have to check each row
                print first_row
                raise Exception('Matching data found, data already imported', first_row)
        if not self.flight and self.config['flight_required']:
            # read the first timestamp and find a flight for it
            self.flight = getFlight(self.get_start_time(), self.vehicle)
            if self.flight:
                self.config['defaults']['flight_id'] = self.flight.id
            else:
                print " ABORTING: NO FLIGHT FOUND"
                # TODO for subsea we will have new rows in existing files so we have to check each row
                print first_row
                raise Exception('No flight found but flight required', first_row)
        return self.config


class CsvSetImporter:
    """
    This class manages collections of CSV files using the CsvImporter to handle them as a collection

    It assumes that telemetry files are in lexicographic and chronological order, so that opening files
    in lex order keeps them in chron order, and that when one file runs out the first line of the next
    file is the next telemetry value
    """
    def __init__(self, yaml_file_path, csv_file_list, vehicle_name=None, flight_name=None, timezone_name='UTC',
                 defaults=None, force=False, replace=False, skip_bad=False):
        """
        Initialize with a path to a configuration yaml file and a list of csv files
        :param yaml_file_path: The path to the yaml self.configuration file for import
        :param csv_file_path: The path to the csv file to import
        :param vehicle_name: The name of the vehicle
        :param flight_name: The name of the flight
        :param timezone_name: The name of the time zone, defaults to UTC
        :param defaults: Optional additional defaults to add to objects
        :param force: force load even if data already exists
        :param replace: replace rows instead of creating new ones, matches based on timestamp.
        :param skip_bad: True to skip loading a row if it has bad/unparsable data
        :return: the imported items
        """

        # YAML config for telemetry files
        self.yaml_file_path = yaml_file_path
        # ordered list of files
        self.files = csv_file_list
        self.file_index = 0
        # telemetry entries to be loaded from files
        self.telemetry = None
        self.telemetry_index = 0
        # Initialize csv importer and load the first file
        self.csv_importer = CsvImporter(yaml_file_path, csv_file_list[0],
                                        vehicle_name=vehicle_name, flight_name=flight_name, timezone_name=timezone_name,
                                        defaults=defaults, force=force, replace=replace, skip_bad=skip_bad)
        self.open_next_csv_file()

    def open_next_csv_file(self):
        if self.file_index >= len(self.files):
            raise StopIteration
        self.csv_importer.open_csv(self.files[self.file_index])
        #self.telemetry = self.csv_importer.load_to_list()
        self.file_index += 1

    def __iter__(self):
        self.file_index = 0
        #self.telemetry_index = 0
        self.open_next_csv_file()
        return self

    def next(self):
        try:
            val = next(self.csv_importer)
            return val
        except StopIteration:
            self.open_next_csv_file()
            val = next(self.csv_importer)
            return val
