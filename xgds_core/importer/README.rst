

=======================================================
Description of files in this directory
=======================================================

.. _TimestampValidator:

Timestamp Validator
~~~~~~~~~~~~~~~~~~~

The first step of our import process is to validate the timestamps in the incoming data, to make sure it can be imported.
This uses a yaml file registry for describing expected time formats.

+--------------------------------------------+------------------------------------------------+
|Filename                                    |Description                                     |
+============================================+================================================+
|``validate_timestamps.py``                  |Script to analyze files and contents times      |
+--------------------------------------------+------------------------------------------------+
|``example/timestamp_validator_config.yaml`` |sample config for validate_timestamps           |
+--------------------------------------------+------------------------------------------------+

.. _ImportHandler:

Import Handler
~~~~~~~~~~~~~~

The Import Handler is found in ../scripts, linked from xgds_core.
It is called as follows:

.. code-block:: bash

./apps/xgds_braille_app/scripts/importHandler.py --username xgds --password ##pwhere## /home/xgds/xgds_braille/apps/xgds_braille_app/importer/ImportHandlerConfig.yaml

The last argument is the configuration file for how it will process other data.  There are 2 such configuration files in this directory:

+-------------------------------------+-------------------------------------------+
|Filename                             |Description                                |
+=====================================+===========================================+
|``importHandler.py``                 |The main import handler script to run      |
|                                     |all the imports recursively, see above     |
+-------------------------------------+-------------------------------------------+
|``example/importHandlerConfig.yaml`` |sample config file for import handler      |
+-------------------------------------+-------------------------------------------+


.. _YamlFiles:

Yaml Model Builder
~~~~~~~~~~~~~~~~~~

To generate code, make migrations and migrate the database based on the newly created model code.
Run as follows:

.. code-block:: bash

source sourceme.sh
./apps/xgds_core/importer/yamlModelBuilder.py <path/to/yaml/file>


+------------------------------+-------------------------------------------+
|Filename                      |Description                                |
+==============================+===========================================+
|``yamlModelBuilder.py``       |Running this will generate code from a     |
|                              |yaml file and update the database.         |
|                              |sample yaml files are in                   |
|                              |../../../docs/examples                     |
+------------------------------+-------------------------------------------+

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
