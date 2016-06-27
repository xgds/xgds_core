# __BEGIN_LICENSE__
#Copyright (c) 2015, United States Government, as represented by the 
#Administrator of the National Aeronautics and Space Administration. 
#All rights reserved.
# __END_LICENSE__

from django import template
from xgds_core.models import Constant

register = template.Library()

@register.simple_tag(name='constant')
def constant(name):
    try:
        return Constant.objects.get(name=name)
    except:
        return None
    
@register.simple_tag(name='constant_value')
def constant_value(name):
    try:
        return Constant.objects.get(name=name).value
    except:
        return None


