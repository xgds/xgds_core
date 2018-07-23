#! /usr/bin/env python
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
Script to read yaml file, create django models and use migration to create database tables.
"""
import re
import sys
import subprocess
from collections import OrderedDict

import django
django.setup()

from django.conf import settings
from csvImporter import load_yaml

INDENT = '    '


def get_field_model_type(field_type):
    """
    Convert the simple field type string to a field model type, ie
    float -> FloatField
    iso8601 -> DateTimeField
    unixtime_float_second -> DateTimeField
    unixtime_int_microsecond -> DateTimeField
    boolean -> BooleanField
    These are then used to look up the database data type from the connection
    :param field_type: incoming simple field type (string)
    :return: the field model type
    """
    if field_type == 'string':
        return 'CharField'
    if field_type in ['iso8601', 'unixtime_float_second', 'unixtime_int_microsecond']:
        return 'DateTimeField'
    if field_type == 'nullboolean':
        return 'NullBooleanField'
    return field_type.capitalize() + 'Field'


def create_field_code(field_name, field):
    """
    Create the one line of code to define a field in a model
    :param field_name: the name of the field
    :param field: the dictionary defining the field
    :return: Python code in a string
    """
    # Default parameters for all model fields
    params = {'blank': 'True',
              'null': 'True'}

    # Max length parameter for strings
    if 'max_length' in field:
        params['max_length'] = field['max_length']
    elif field['type'] == 'string':
        params['max_length'] = 256

    # If there is a timestamp field make it a db_index and make it required
    if 'timestamp' == field_name:
        params['db_index'] = 'True'
        params['blank'] = 'False'
        params['null'] = 'False'

    # build the string
    result = '%s%s = models.%s(' % (INDENT, field_name, get_field_model_type(field['type']))
    result += ', '.join(['%s=%s' % (pk, pv) for pk, pv in params.iteritems()])
    result += ')\n'

    return result


def create_channel_description(field_name, field):
    """
    Create the channel description dictionary
    :param field: the dictionary defining the field
    :return: the string for construction of the channel description
    """
    result = "xgds_timeseries.ChannelDescription("
    if 'label' in field:
        result += "'%s'" % field['label']
    else:
        result += "'%s'" % field_name.capitalize()

    if 'units' in field:
        result += ", units='%s'" % field['units']

    if 'min' in field:
        result += ", global_min=%f" % field['min']
    if 'max' in field:
        result += ", global_max=%f" % field['max']
    if 'interval' in field:
        result += ", interval=%f" % field['interval']

    result += ")"
    return result


def create_model_code(config, yaml_file, model_name):
    """
    Create the model code based on the config
    :param config: The config file we are using (loaded from yaml)
    :return: The python code to inject in models.py
    """

    # add space
    result = '\n'

    # the class itself
    superclass = 'models.Model'
    if 'superclass' in config:
        superclass = config['superclass']
    result += 'class %s(%s):\n' % (model_name, superclass)

    # add comment
    result += '%s"""\n%sThis is an auto-generated Django model created from a\n' % (INDENT, INDENT)
    result += '%sYAML specifications using %s\n' % (INDENT, sys.argv[0])
    result += '%sand YAML file %s\n%s"""\n\n' % (INDENT, yaml_file, INDENT)

    time_field = 'timestamp'
    if 'time_field' in config:
        time_field = config['time_field']

    channel_descriptions = OrderedDict()
    for field_name, field_info in config['fields'].iteritems():
        result += create_field_code(field_name, field_info)
        if field_name != time_field:
            channel_descriptions[field_name] = create_channel_description(field_name, field_info)

    # special case the foreign key to a flight, if required
    if 'flight_required' in config and config['flight_required']:
        result += "%sflight = models.ForeignKey('%s', on_delete=models.SET_NULL, blank=True, null=True)\n" % (INDENT, settings.XGDS_CORE_FLIGHT_MODEL)

    # set the stateful flag if it is true, defaults to false
    if 'stateful' in config and config['stateful']:
        result += "%sstateful=True\n" % INDENT

    # add the title, splitting out camelcase
    result += '\n'
    splits = re.sub('([a-z])([A-Z])', r'\1 \2', model_name).split()
    title = ''
    for s in splits:
        title = title + ' ' + s
    result += "%stitle = '%s'" % (INDENT, title[1:])

    # add the channel descriptions
    result += '\n'
    result += "%schannel_descriptions = {\n" % INDENT
    for key, value in channel_descriptions.iteritems():
        result += "%s%s%s%s%s%s%s'%s': %s,\n" % (INDENT, INDENT, INDENT, INDENT, INDENT, INDENT, INDENT, key, value)
    result += "%s%s%s%s%s%s%s}\n" % (INDENT, INDENT, INDENT, INDENT, INDENT, INDENT, INDENT)

    # add the channel classmethod
    result += '\n'
    result += '%s@classmethod\n' % INDENT
    result += '%sdef get_channel_names(cls):\n' % INDENT
    result += '%s%sreturn [' % (INDENT, INDENT)
    for key, value in channel_descriptions.iteritems():
        result += "'%s', " % key
    result +=']\n'

    # add the custom time field name if need be
    if time_field != 'timestamp':
        result += '%s@classmethod\n' % INDENT
        result += '%sdef get_time_field_name(cls):\n' % INDENT
        result += "%s%sreturn '%s'\n" % (INDENT, INDENT, time_field)

    # add another space
    result += '\n'
    return result


def model_exists(app_name, model_name):
    """
    Test if the model already exists
    :param app_name:
    :param model_name:
    :return: True if it exists, False otherwise
    """

    try:
        exec('from %s.models import %s' % (app_name, model_name))
        print 'The model already exists %s.%s' % (app_name, model_name)
        return True
    except ImportError:
        return False


def main():
    # YAML files are specified on the command line
    yaml_files = sys.argv[1:]

    apps_needing_migration = set()

    for yaml_file in yaml_files:
        config = load_yaml(yaml_file)
        split_name = config['class'].split('.')
        app_name = split_name[0]
        model_name = split_name[1]

        if model_exists(app_name, model_name):
            continue
        model_code = create_model_code(config, yaml_file, model_name)
        print model_code

        # write to models.py
        model_file_name = './apps/%s/models.py' % app_name
        model_file = open(model_file_name, 'a')
        model_file.write(model_code)
        model_file.close()
        print 'Updated %s' % model_file_name

        # write to admin.py
        admin_file_name = './apps/%s/admin.py' % app_name
        admin_file = open(admin_file_name, 'a')
        admin_file.write('admin.site.register(%s)\n' % model_name)
        admin_file.close()
        print 'Updated %s' % admin_file_name

        # add to the set of apps needing migration
        apps_needing_migration.add(app_name)

    # do the migrations; since we've modified models.py we have to run this in a new process.
    if apps_needing_migration:
        for app_name in apps_needing_migration:
            print 'Making migrations for %s (be patient)' % app_name
            subprocess.call(['./manage.py', 'makemigrations', app_name])
        print 'Migrating'
        subprocess.call(['./manage.py', 'migrate'])


if __name__ == '__main__':
    main()
