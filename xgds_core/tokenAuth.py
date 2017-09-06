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

from django import db
from django.contrib import auth
from rest_framework.authtoken.models import Token

UserModel = auth.get_user_model()


def check_password(environ, username, password):
    """                                                                                                                                                                                            
    Authenticates against Django's auth database but supports token auth as well
    Called by wsgi                                                                                                                                                  
                                                                                                                                                                                                   
    mod_wsgi docs specify None, True, False as return value depending                                                                                                                              
    on whether the user exists and authenticates.                                                                                                                                                  
    """

    # db connection state is managed similarly to the wsgi handler                                                                                                                                 
    # as mod_wsgi may call these functions outside of a request/response cycle
    db.reset_queries()

    try:
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            return None
        if not user.is_active:
            return None
        if user.check_password(password):
            return True
        else:
            try:
                foundToken = Token.objects.get(user=user, key=password)
                return True
            except:
                return False
    finally:
        db.close_old_connections()
