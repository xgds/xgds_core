#__BEGIN_LICENSE__
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
#__END_LICENSE__

import re
from django import template
from django.conf import settings
from django.db import models, DatabaseError, IntegrityError
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
try:
    from django.contrib.contenttypes.fields import GenericForeignKey
except ImportError:
    from django.contrib.contenttypes.generic import GenericForeignKey
try:
    from django.utils.html import format_html
    from django.db import OperationalError
except ImportError:
    pass

from string import capwords

integer_test = re.compile(r'^\d+$')
numeric_test = re.compile(r'^[\.\-Ee\d]+$')
register = template.Library()


# http://stackoverflow.com/questions/844746/performing-a-getattr-style-lookup-in-a-django-template
def getattribute(obj, attr):
    """Gets an attribute of an object dynamically from a string name"""

    try:
        return getattr(obj, attr)
    except (TypeError, AttributeError):
        pass
    
    try:
        return obj[attr]
    except (TypeError, AttributeError, KeyError):
        pass

    if integer_test.match(str(attr)) and len(obj) > int(attr):
        v = obj[int(attr)]
    elif isinstance(attr, models.Field):
        try:
            v = getattr(obj, attr.name)
        except (ObjectDoesNotExist, OperationalError, DatabaseError, IntegrityError) as expt:
            # can happen with an inconsistent database, as in plrp
            print(obj,attr.name)
            print(expt)
            # No problem, we love dirty data!
            v = None
    elif isinstance(attr, GenericForeignKey):
        v = getattr(obj, attr.name , None)
    else:
        v = settings.TEMPLATE_STRING_IF_INVALID
    if (isinstance(v, models.Manager)):
        v = v.all()

    return v


register.filter('getattribute', getattribute)


def modelName(instance):
    return instance._meta.object_name


register.filter('modelName', modelName)


def moduleName(instance):
    return instance._meta.app_label


register.filter('moduleName', moduleName)


def displayLinkedData(value):
    if value is None:
        return None
    else:
        try:
            url = value.get_absolute_url()
        except AttributeError:
            return None
        try:
            return format_html(u'<A HREF="{0}">{1}</A>',mark_safe(url),unicode(value))
        except NameError:
            return mark_safe('<A HREF="' + url + '">'+ unicode(value) + '</A>')

        ##return mark_safe('<A HREF="' + url + '">'+ unicode(display(field.rel.to,value)) + '</A>')
        

# def stringifyList(field,lst):
#     """
#     """
#     results = []
#     if (len(lst) > 100):
#         for v in lst[0:4]:
#             results.append(displayLinkedData(field,v))
#         results.append("...")
#         for v in lst[len(results)-4:len(results)]:
#             results.append(displayLinkedData(field,v))

#         results.append("("+str(len(lst))+" records)")
#     else:
#         for v in lst:
#             results.append(displayLinkedData(field,v))
#     return mark_safe(','.join(results))   


def display(field, value):
    """Returns html snippet appropriate for value and field"""
    try:
        value.last_name
        ##return ', '.join([value.last_name, value.first_name])
        return label(value)
    except AttributeError:
        if isinstance(field, models.ImageField):
            if value == '':
                return ''
            else:
                try:
                    return format_html(u'<A HREF="{0}"><IMG SRC="{1}" WIDTH="100"></A>',
                                       mark_safe(field.storage.url(value)),
                                       mark_safe(field.storage.url(value)))
                except NameError:
                    return mark_safe('<A HREF="' + field.storage.url(value) + '"><IMG SRC="' + field.storage.url(value) + '" WIDTH="100"></A>')
        elif isinstance(field, (models.ForeignKey, models.OneToOneField)):
            return displayLinkedData(value)
        elif isinstance(field, GenericForeignKey):
            if value is not None:
                return displayLinkedData(value)
            else:
                return value
        # elif isinstance(field, models.ManyToManyField):
        #     results = []
        #     if (len(value) > 100):
        #         for v in value[0:4]:
        #             results.append(displayLinkedData(field,v))
        #         results.append("...")
        #         for v in value[len(results)-4:len(results)]:
        #             results.append(displayLinkedData(field,v))

        #         results.append("("+str(len(value))+" records)")
        #     else:
        #         for v in value:
        #             results.append(displayLinkedData(field,v))
        #     return mark_safe(','.join(results))   
        elif isinstance(field, models.fields.files.FileField):
            if value.name:
                try:
                    return format_html(u'<A HREF="{0}">{1}</A>',mark_safe(field.storage.url(value)),value.name)
                except NameError:
                    return mark_safe(u'<A HREF="{0}">{1}</A>'.format(field.storage.url(value)),value.name)
            else:
                return ""
        elif isinstance(value, User):
            return ', '.join([value.last_name, value.first_name])
        elif isinstance(value, basestring):
            return value
        else:
            try:
                results = []
                try:
                    cnt = value.count()
                except (TypeError, AttributeError):
                    cnt = len(value)
                if (cnt > 100):
                    for v in value[0:4]:
                        results.append(displayLinkedData(v))
                    results.append("...")
#                    for v in value[len(results)-4:len(results)]:
#                       results.append(displayLinkedData(v))

                    results.append("("+str(len(value))+" records)")
                else:
                    for v in value:
                        results.append(displayLinkedData(v))
                return mark_safe(','.join(results))   
                # ##foo = ', '.join([displayLinkedData(v) for v in value])
                # foo = stringifyList(field,value)
                # return mark_safe(foo)
            except AttributeError:
                return "Error"
            except TypeError:
                return value
            except ValueError:
                return None

register.filter('display', display)


def modulo(value, arg):
    """Computes value % arg"""

    return value % arg

register.filter('modulo', modulo)


def isNumeric(value):
    """tests to see if this is a number or not"""
    try:
        value.__iter__
        return False
    except AttributeError:
        return numeric_test.match(str(value))

register.filter('isNumeric', isNumeric)


def divide(value, arg):
    """Computes value / arg"""

    return float(value) / float(arg)

register.filter('divide', divide)


def addfloat(value, arg):
    """Computes value + arg"""

    return float(value) + float(arg)

register.filter('addfloat', addfloat)


def dorange(value, arg):
    """access to range function"""
    return range(value, arg)

register.filter('range', dorange)


def verbose_name(field):
    """Get the verbose name, or make one up if undefined"""
    try:
        return field.verbose_name
    except:
        return capwords(re.sub( r"([A-Z])", r" \1", field.name))

register.filter('verbose_name', verbose_name)
