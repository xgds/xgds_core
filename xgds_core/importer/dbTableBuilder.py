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
from django.db import connection
from django.conf import settings

from geocamUtil.loader import LazyGetModelByName

from csvImporter import load_yaml

"""
Utilities for building database tables from yaml file specification.
see ../../docs/dataImportYml.rst
"""


def create_table_name(name):
    """
    Starting from a class name create the table name
    eg xgds_braille_appp.RoverDistance -> xgds_braille_app_roverdistance
    :param name: input class name
    :return: table name
    """
    return name.replace('.', '_').lower()


def check_table_exists(tablename, cursor):
    """
    Check if the table exists
    :param tablename: the exact name of the table
    :param cursor: connection cursor
    :return: True if exists, False otherwise
    """
    sql = "show tables like '%s';" % tablename
    result = cursor.execute(sql)
    if result:
        return True
    return False


def get_field_model_type(field_type):
    """
    Convert the simple field type string to a field model type, ie
    float -> FloatField
    datetime -> DateTimeField
    boolean -> BooleanField
    These are then used to look up the database data type from the connection
    :param field_type: incoming simple field type (string)
    :return: the sql for the database data type
    """
    if field_type == 'string':
        return connection.data_types['CharField']
    if field_type == 'datetime':
        return connection.data_types['DateTimeField']
    if field_type == 'nullboolean':
        return connection.data_types['NullBooleanField']
    return connection.data_types[field_type.capitalize() + 'Field']


def quote_name(name):
    return "`%s`" % name


def build_column_sql(field):
    """
    Build the string for creating the column for a field
    :param field: the field dictionary
    :return: the sql string or None
    """
    if 'skip' in field:
        return None
    sql = get_field_model_type(field['type'])
    if not sql:
        return None

    if 'CharField' in sql:
        if 'max_length' in field:
            max_length = field['max_length']
        else:
            max_length = 256
        sql = sql % max_length

    if 'default' in field:
        sql += " DEFAULT %s" % field['default']

    # TODO user set null? default to nullable?
    sql += " NULL"

    # TODO HANDLE MIN MAX?

    # # FK
    # if field.remote_field and field.db_constraint:
    #     to_table = field.remote_field.model._meta.db_table
    #     to_column = field.remote_field.model._meta.get_field(field.remote_field.field_name).column
    #     if self.connection.features.supports_foreign_keys:
    #         self.deferred_sql.append(self._create_fk_sql(model, field, "_fk_%(to_table)s_%(to_column)s"))
    #     elif self.sql_create_inline_fk:
    #         definition += " " + self.sql_create_inline_fk % {
    #             "to_table": self.quote_name(to_table),
    #             "to_column": self.quote_name(to_column),
    #         }
    return sql


def do_build_table(config, table_name, cursor):
    """
    Actually build the database table
    :param config: The full config loaded from the yaml
    :param table_name: the cleaned up table name
    :param cursor: database connection cursor
    :return:
    """
    column_sqls = ["`id` int(11) NOT NULL AUTO_INCREMENT"]
    for field_name, field in config['fields'].iteritems():
        column = build_column_sql(field)
        if column:
            column_sqls.append("%s %s" % (
                quote_name(field_name),
                column,
            ))

    for field_name, field in config['defaults'].iteritems():
        column = build_column_sql(field)
        if column:
            column_sqls.append("%s %s" % (
                quote_name(field_name),
                column,
            ))

    if 'flight_required' in config:
        flight_table_name = LazyGetModelByName(settings.XGDS_CORE_FLIGHT_MODEL).get()._meta.db_table
        column_sqls.append("`flight_id` int(11) DEFAULT NULL")
        column_sqls.append("CONSTRAINT `%s_flight_id` FOREIGN KEY(`flight_id`) REFERENCES `%s`(`id`)" % (table_name, flight_table_name))

    column_sqls.append("PRIMARY KEY (`id`)")

    # Make the table
    full_sql = connection.schema_editor().sql_create_table % { "table": quote_name(table_name),
                                                               "definition": ", ".join(column_sqls)}

    print full_sql
    cursor.execute(full_sql)


def build_table(yaml_file_path):
    """
    Build the database table based on the classname
    :param yaml_file_path: the path to the yaml file
    :return: True if it worked
    """
    config = load_yaml(yaml_file_path)
    table_name = create_table_name(config['class'])
    cursor = connection.cursor()

    if check_table_exists(table_name, cursor):
        print 'Table %s already exists' % table_name
        # TODO do we have to close the connection?
        return False

    do_build_table(config, table_name, cursor)

    if check_table_exists(table_name, cursor):
        print 'Created %s' % table_name
        return True



