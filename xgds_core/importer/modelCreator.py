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
Script to read yaml file, create database tables and use introspection to construct models.
This is a **starting point**
"""

import django
django.setup()

from csvImporter import load_yaml
from dbTableBuilder import build_table

from django.core import management
from django.conf import settings

table_names = []

def check_table_name(name):
    return name in table_names


def to_camel(input):
    """
    Take an underscore-separated input string and camelcase it, ie:
    xgds_braille_app -> XgdsBrailleApp
    :param input: input string
    :return: camelcase output string
    """
    splits = input.split('_')
    return "".join(split.capitalize() for split in splits)


def replace(variable, old_phrase, new_phrase=''):
    """
    Replace a phrase in a string
    :param variable: the string
    :param old_phrase: the phrase to replace, defaults to ''
    :param new_phrase: the phrase to replace it with
    :return: the updated string
    """
    variable = variable.replace(old_phrase, new_phrase)
    return variable


def generate_code(table_name, config):
    """
    Generate the model code to go along with the new table.
    :param table_name: the name of the table in the database to use to create the model
    :param config: the config loaded from the yaml file
    :return: the cleaned up block of code to insert into the correct models.py file
    """
    table_names.append(table_name)

    tmp_model_file = open('/tmp/%s.py' % table_name, 'w+')
    management.call_command('inspectdb', table_name_filter=check_table_name, stdout=tmp_model_file)
    tmp_model_file.seek(0)
    new_source = tmp_model_file.read()
    tmp_model_file.close()

    # replace the jammed together camelcase flight name
    flight_class_name = settings.XGDS_CORE_FLIGHT_MODEL
    split_flight_class_name = flight_class_name.split('.')
    replace_flight_class_name = to_camel(split_flight_class_name[0]) + split_flight_class_name[1]
    new_source = replace(new_source, replace_flight_class_name, flight_class_name)

    # replace the jammed together camelcase class name
    full_class_name = config['class']
    split_full_class_name = full_class_name.split('.')
    replace_full_class_name = to_camel(split_full_class_name[0]) + split_full_class_name[1]
    new_source = replace(new_source, replace_full_class_name, split_full_class_name[1])

    # replace the managed = false
    new_source = replace(new_source, 'managed = False\n')
    new_source = replace(new_source, '#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table\n')

    # replace the class it inherits from
    # new_source = replace(new_source, '(models.Model)','(xgds_plot.TimeSeries)')
    return new_source


def main():
    import optparse

    parser = optparse.OptionParser('usage: -c config path')
    parser.add_option('-c', '--config', help='path to config file (yaml)')

    opts, args = parser.parse_args()

    if not opts.config:
        parser.error('config is required')

    config = load_yaml(opts.config)
    table_name = build_table(config)
    if table_name:
        new_source = generate_code(table_name, config)
        print 'GENERATED SOURCE CODE:'
        print new_source

        if new_source:
            app_name = config['class'].split('.')[0]
            model_file_name = './apps/%s/models.py' % app_name
            model_file = open(model_file_name, 'a')
            model_file.write(new_source)
            model_file.close()



if __name__ == '__main__':
    main()
