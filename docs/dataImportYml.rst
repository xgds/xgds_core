
=======================================================
The Data Import YAML Format Specification
=======================================================

Authors
  | Tamar Cohen (NASA Ames Research Center)
  | David Lees (Carnegie Mellon University)

Revision
  0.1

Date
  04/09/2018


Further information
  http://yaml.org/

.. contents::
   :depth: 2

.. sectnum::

Introduction
============

Data Import YAML is a format for specifying the bindings between xGDS models and comma or tab separated values.
When data is imported from a csv (or tsv) file, the columnar data for each row is mapped via a Data Import YAML file
to model field data.


Examples
========

KRex2_PastPosition.yaml::

   # This file describes poses provided by KRex2 as part of the BRAILLE project
   name: KRex2.PastPosition
   class: xgds_braille_app.PastPosition
   extension: tsv
   delimiter: \t
   fields:
   - name: vehicle__name
     default: KRex2
     type: string
   - name: timestamp
     type: datetime
   - name: longitude
     type: float
     min: -180.0
     max: 180.0
   - name: latitude
     type: float
     min: -90.0
     max: 90.0
     units: degrees
   - name: altitude
     type: float
     units: meters
   - name: yaw
     type: float
     min: -math.pi
     max: math.pi
     units: radians
   - name: pitch
     type: float
     min: -math.pi
     max: math.pi
     units: radians
   - name: roll
     type: float
     min: -math.pi
     max: math.pi
     units: radians

Hercules_TempProbe.yaml::

   name:Hercules.TempProbe
   class: xgds_subsea_app.TempProbe
   extension: TEM
   delimiter: \t
   defaults:
    - name: vehicle__name
      value: Hercules
   fields:
    - name: data_type
      default: TEM
      type: string
      skip: true
    - name: timestamp
      type: datetime
    - name: instrument_name
      type: string
      default: TEMPPROBE
    - name: temperature_group
      # This does not map to a field, instead the regex causes child fields to be used based on the content of the row, eg 81.3C becomes 81.3 temperature and C units
      type: regex
      regex: (-?\d*[.]*\d*)([KFCkfc])+
      fields:
      - name : temperature
        type : float
      - name: units
        type: string
        default: C

Definitions
===========

 * The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
   "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
   document are to be interpreted as described in `RFC 2119`_.

 * YAML elements are defined here: http://yaml.org/spec/1.2/spec.html
   Data Import YAML documents have the standard YAML type, "application/x-yaml".


Class Hierarchy
===============

The  objects that make up Data Import YAML documents fit into a class
hierarchy as follows:

 * MetadataSpecification_

 * DefaultSpecification_

 * FieldSpecification_

 * ChildSpecification_


All structures are collections of name/value pairs where the names
are strings.

.. _MetadataSpecification:

Metadata Specification
~~~~~~~~~~~~~~~~~~~~~~

Metadata has a ``type`` member that states which class it
belongs to. The definition of that class specifies the name, type, and
interpretation of other members.

+------------------+----------------+-----------------+------------------------------------+
|Member            |Type            |Values           |Meaning                             |
+==================+================+=================+====================================+
|``name``          |string          |required         |The name of the data importer       |
+------------------+----------------+-----------------+------------------------------------+
|``class``         |string          |required         |The fully qualified Python name of  |
|                  |                |                 |the Django model that will be used  |
|                  |                |                 |for data import described by this   |
|                  |                |                 |Data Import YAML file.              |
+------------------+----------------+-----------------+------------------------------------+
|``extension``     |string          |                 |File extension for import files.    |
+------------------+----------------+-----------------+------------------------------------+
|``delimiter``     |string          |optional         |Whatever character will be used     |
|                  |                |                 |to separate data, , or `\t` usually |
+------------------+----------------+-----------------+------------------------------------+
|``defaults``      |list            |optional         |A list of defaults                  |
+------------------+----------------+-----------------+------------------------------------+
|``fields``        |list            |required         |A list of field specifications.     |
+------------------+----------------+-----------------+------------------------------------+
|``children``      |list            |optional         |A list of child specifications;     |
|                  |                |                 |these will be nested models.        |
+------------------+----------------+-----------------+------------------------------------+

.. _DefaultSpecification:

Default Specification
~~~~~~~~~~~~~~~~~~~~~

A Default Specification defines name value pairs for any fields that should be set but are
not part of the data imported.

+-------------------+----------------+-----------------+------------------------------------+
|Member             |Type            |Values           |Meaning                             |
+===================+================+=================+====================================+
|``name``           |string          |required         |The exact name of the Python model  |
|                   |                |                 |field                               |
+-------------------+----------------+-----------------+------------------------------------+
|``value``          |                |                 |The value to assign to the field.   |
+-------------------+----------------+-----------------+------------------------------------+

.. _FieldSpecification:

Field Specification
~~~~~~~~~~~~~~~~~~~

A Field Specification defines the mapping between the columnar data in the import file and 
the Python model fields.

+------------------+----------------+-----------------+------------------------------------+
|Member            |Type            |Values           |Meaning                             |
+==================+================+=================+====================================+
|``name``          |string          |required         |The exact name of the Python model  |
|                  |                |                 |field.                              |
+------------------+----------------+-----------------+------------------------------------+
|``type``          | string         |string           |The type                            |
|                  |                |int              |                                    |
|                  |                |float            |                                    |
|                  |                |boolean          |                                    |
|                  |                |DateTime         |                                    |
|                  |                |regex            |                                    |
+------------------+----------------+-----------------+------------------------------------+
|``skip``          |boolean         |false            |True if this columnar data does not |
|                  |                |                 |map to a model field.               |
+------------------+----------------+-----------------+------------------------------------+
|``default``       |                |optional         |Default value                       |
+------------------+----------------+-----------------+------------------------------------+
|``min``           |                |optional         |Minimum value, inclusive            |
+------------------+----------------+-----------------+------------------------------------+
|``max``           |                |optional         |Maximum value, inclusive            |
+------------------+----------------+-----------------+------------------------------------+
|``units``         |string          |optional         |The expected units of measure       |
+------------------+----------------+-----------------+------------------------------------+
|``regex``         |regex string    |optional         |Regex to use to parse the value.    |
+------------------+----------------+-----------------+------------------------------------+
|``fields``        |list            | optional        |In the case of a regex field, this  |
|                  |                |                 |will process the regex values into  |
|                  |                |                 |the specified model fields. They    |
|                  |                |                 |are not nested within the model;    |
|                  |                |                 |it is a flat model object.          |
+------------------+----------------+-----------------+------------------------------------+

.. _ChildSpecification:

Child Specification
~~~~~~~~~~~~~~~~~~~

A Child Specification defines metadata and fields that are part of the child model.  This is a one to many relationship; the parent
class (described in the metadata or container) is one, and can contain many children.

+------------------+----------------+-----------------+------------------------------------+
|Member            |Type            |Values           |Meaning                             |
+==================+================+=================+====================================+
|``name``          |string          |required         |The readable name of the model      |
+------------------+----------------+-----------------+------------------------------------+
|``class``         |string          |required         |The fully qualified Python name of  |
|                  |                |                 |the Django model that will be used  |
|                  |                |                 |for data import described by this   |
|                  |                |                 |Data Import YAML file.              |
+------------------+----------------+-----------------+------------------------------------+
|``defaults``      |list            |optional         |A list of defaults                  |
+------------------+----------------+-----------------+------------------------------------+
|``fields``        |list            |required         |A list of field specifications.     |
+------------------+----------------+-----------------+------------------------------------+
|``children``      |list            |optional         |A list of child specifications;     |
|                  |                |                 |these will be nested models.        |
+------------------+----------------+-----------------+------------------------------------+

Future Work
===========

* Data Import YAML should be able to specify flat files (csv / tsv) which contain multiple types of data in one file,
  for example the .NAV file from OET, wherein each row describes navigation information for differing vehicles.


.. _ISO 8601: http://www.w3.org/TR/NOTE-datetime

.. _RFC 2119: https://www.ietf.org/rfc/rfc2119.txt

.. _Python String Formatting: http://docs.python.org/3/library/string.html#formatstrings

.. o __BEGIN_LICENSE__
.. o  Copyright (c) 2015, United States Government, as represented by the
.. o  Administrator of the National Aeronautics and Space Administration.
.. o  All rights reserved.
.. o 
.. o  The xGDS platform is licensed under the Apache License, Version 2.0
.. o  (the "License"); you may not use this file except in compliance with the License.
.. o  You may obtain a copy of the License at
.. o  http://www.apache.org/licenses/LICENSE-2.0.
.. o 
.. o  Unless required by applicable law or agreed to in writing, software distributed
.. o  under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
.. o  CONDITIONS OF ANY KIND, either express or implied. See the License for the
.. o  specific language governing permissions and limitations under the License.
.. o __END_LICENSE__
