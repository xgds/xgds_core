# __BEGIN_LICENSE__
#Copyright (c) 2015, United States Government, as represented by the 
#Administrator of the National Aeronautics and Space Administration. 
#All rights reserved.
# __END_LICENSE__

from django import template
from geocamUtil.UserUtil import getUserName

register = template.Library()

@register.simple_tag(name='userName')
def userName(user):
    try:
        return getUserName(user)
    except:
        return user


