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

import logging
import string

from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User

from django.core import mail

from django.conf import settings
from xgds_core.registerForms import UserRegistrationForm, EmailFeedbackForm
from rest_framework.authtoken.models import Token
from django.http import JsonResponse


registration_email_template = string.Template(  # noqa
"""
Greetings, xGDS managers.

You have received a user registration request for $first_name $last_name.

Username: $username
Email: $email

$first_name says:
"$comments"

To activate this user, visit:
$url

The request came from $ip_address, and was referred by the form at $referrer
"""
)


def registerUser(request):
    if request.method not in ('GET', 'POST'):
        raise Exception("Invalid request method: " + request.method)
    # if request.user.is_authenticated:
    #    # Don't let them register again if they're already logged in.
    #    #return HttpResponseRedirect('/')
    #    return HttpResponse("You are already logged in.")
    if request.method == "GET":
        return render(request,
                      "registration/register.html",
                      {'register_form': UserRegistrationForm()}
                      )
    else:
        form = UserRegistrationForm(request.POST)

        if not form.is_valid():
            # FAIL
            logging.info("Create form validation failed.")
            return render(request,
                          "registration/register.html",
                          {'register_form': form})
        else:
            logging.info("Creating a new user")
            user_data = form.cleaned_data
            assert user_data.get('email')
            user = User.objects.create_user(user_data['username'], user_data['email'], user_data['password1'])
            user.first_name = user_data['first_name']
            user.last_name = user_data['last_name']
            user.is_active = False
            user.save()
            mail.mail_managers(
                'Registration request from %s %s (%s)' % (user.first_name, user.last_name, user.username),
                registration_email_template.substitute({
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'url': request.build_absolute_uri(reverse('user-activate', args=[user.id])),
                    'comments': user_data['comments'],
                    'ip_address': request.META['REMOTE_ADDR'],
                    'referrer': request.META['HTTP_REFERER'],
                }),
            )
            return render(request,
                          "registration/simple_message.html",
                          {'message': "You will receive an email notification at %s after a site manager approves your request." % user.email},
                          )


@permission_required('add_user')
def activateUser(request, user_id):

    def render_message(msg):
        return render(request,
                      "registration/simple_message.html",
                      {'message': msg},
                      )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return render_message("No user with the given id")

    if user.is_active:
        return render_message("The user %s has already been activated.  Someone must have gotten here first." % user.username)

    user.is_active = True
    user.save()
    mail.send_mail(
        settings.EMAIL_SUBJECT_PREFIX + "Your account has been activated",
        string.Template("""
        Hi, $first_name.
        Your xGDS registration request has been approved.  Click to log in!
        $url
        """).substitute({'username': user.username,
                         'first_name': user.first_name,
                        'url': request.build_absolute_uri(reverse('user-login'))}),
        settings.SERVER_EMAIL,
        [user.email],
    )
    mail.mail_managers(
        settings.EMAIL_SUBJECT_PREFIX + "The user %s was activated." % user.username,
        string.Template("""
        The user $first_name $last_name ($username) was successfully activated by $adminuser.
        """).substitute({'username': user.username,
                         'first_name': user.first_name,
                         'last_name': user.last_name,
                        'adminuser': request.user.username}),
    )
    return render_message("The user %s %s (%s) was successfully activated." % (user.first_name, user.last_name, user.username))


def email_feedback(request):
    mail_sent = False
    if request.POST:
        form = EmailFeedbackForm(request.POST)
        if form.is_valid():
            cc  = []
            content = form.cleaned_data['email_content']
            fromEmail = form.cleaned_data.get('reply_to', None)
            if fromEmail:
                cc = [request.user.email]
                content = fromEmail + ": " + content
            mail.mail_managers(
                    "XGDS USER FEEDBACK",
                    content,
                    cc)
            mail_sent = True
    else:
        email = None
        if hasattr(request.user, 'email'):
            email = request.user.email
        form = EmailFeedbackForm(initial={'reply_to': email})
    return render(request,
                  'registration/email_feedback.html',
                  {'form': form,
                   'mail_sent': mail_sent},
                  )


def generateAuthToken(request, username):
    user = request.user
    if username:
        user = User.objects.get(username=username)
    token = Token.objects.get_or_create(user=user)
    theDict = {'username':user.username,
               'token': token[0].key}
    return JsonResponse(theDict);


def renderTemplate(request, template_name):
    ''' Because TemplateView.as_view does not support post'''
    return render(request, template_name)
