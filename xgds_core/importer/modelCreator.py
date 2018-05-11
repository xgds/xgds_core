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

from dbTableBuilder import build_table

from django.core import management

table_names = []

def check_table_name(name):
    return name in table_names

def main():
    import optparse

    parser = optparse.OptionParser('usage: -c config path')
    parser.add_option('-c', '--config', help='path to config file (yaml)')

    opts, args = parser.parse_args()

    if not opts.config:
        parser.error('config is required')

    table_name = build_table(opts.config)
    if table_name:
        table_names.append(table_name)
        print management.call_command('inspectdb', table_name_filter=check_table_name)


if __name__ == '__main__':
    main()
