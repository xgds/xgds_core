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

from django import forms
from django.forms import ModelForm
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import DateTimeField
from django.utils.functional import lazy

from geocamUtil.loader import LazyGetModelByName

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    comments = forms.CharField(required=False, label="Introduce yourself", widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        # Hack to modify the sequence in which the fields are rendered
        self.fields.keyOrder = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'comments']

    def clean_email(self):
        "Ensure that email addresses are unique for new users."
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email address already exists.")
        return email
    
    class Meta:
        model = User
        fields = ("username",'first_name', 'last_name', 'email', 'password1', 'password2', 'comments')


class EmailFeedbackForm(forms.Form):
    reply_to = forms.EmailField(required=False, label="Your email address")
    email_content = forms.CharField(widget=forms.Textarea, label="Message")


