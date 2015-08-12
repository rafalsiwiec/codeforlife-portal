# -*- coding: utf-8 -*-
# Code for Life
#
# Copyright (C) 2015, Ocado Limited
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ADDITIONAL TERMS – Section 7 GNU General Public Licence
#
# This licence does not grant any right, title or interest in any “Ocado” logos,
# trade names or the trademark “Ocado” or any other trademarks or domain names
# owned by Ocado Innovation Limited or the Ocado group of companies or any other
# distinctive brand features of “Ocado” as may be secured from time to time. You
# must not distribute any modification of this program using the trademark
# “Ocado” or claim any affiliation or association with Ocado or its employees.
#
# You are not authorised to use the name Ocado (or any of its trade names) or
# the names of any author or contributor in advertising or for publicity purposes
# pertaining to the distribution of this program, without the prior written
# authorisation of Ocado.
#
# Any propagation, distribution or conveyance of this program must include this
# copyright notice and these terms. You must not misrepresent the origins of this
# program; modified versions of the program must be marked as such and not
# identified as the original program.
from django import forms
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth import forms as django_auth_forms
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.template import loader
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from portal.models import Student, Teacher
from portal.helpers.password import password_strength_test


class PasswordResetSetPasswordForm(django_auth_forms.SetPasswordForm):
    def __init__(self, user, *args, **kwags):
        super(PasswordResetSetPasswordForm, self).__init__(user, *args, **kwags)
        self.fields['new_password1'].label = "Enter your new password"
        self.fields['new_password1'].widget.attrs['placeholder'] = "Try for least 8 characters, upper and lower case letters, and numbers"
        self.fields['new_password2'].label = "Confirm your new password"
        self.fields['new_password2'].widget.attrs['placeholder'] = "Please repeat your new password"

    def clean_new_password1(self):
        new_password1 = self.cleaned_data.get('new_password1', None)
        if hasattr(self.user.userprofile, 'teacher'):
            if not password_strength_test(new_password1):
                raise forms.ValidationError(
                    "Password not strong enough, consider using at least 8 characters, upper and "
                    + "lower case letters, and numbers")
        elif hasattr(self.user.userprofile, 'student'):
            if not password_strength_test(new_password1, length=6, upper=False, lower=False,
                                          numbers=False):
                raise forms.ValidationError(
                    "Password not strong enough, consider using at least 6 characters")
        return new_password1


class StudentPasswordResetForm(forms.Form):
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={'placeholder': "rosie_f"}))

    def clean_username(self):
        username = self.cleaned_data.get('username', None)
        user_filter = User.objects.filter(username=username)
        # Check such a username exists
        if not user_filter.exists():
            raise forms.ValidationError("Cannot find an account with that username")
        # Check such a username is not in use by a student part of a class/school
        if not Student.objects.filter(class_field=None, user__user__username=username).exists():
            raise forms.ValidationError("Cannot find an account with that username")
        return username

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Sends a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, 'text/html')

        email_message.send()

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None):
        """
        Generates a one-use only link for resetting password and sends to the
        user.
        """
        UserModel = get_user_model()
        username = self.cleaned_data["username"]
        active_users = UserModel._default_manager.filter(
            username=username, is_active=True)
        for user in active_users:
            # Make sure that no email is sent to a user that actually has
            # a password marked as unusable
            if not user.has_usable_password():
                continue
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            context = {
                'email': user.email,
                'domain': domain,
                'site_name': site_name,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
            }

            self.send_mail(subject_template_name, email_template_name,
                           context, from_email, user.email,
                           html_email_template_name=html_email_template_name)


class TeacherPasswordResetForm(forms.Form):
    email = forms.EmailField(
        label='Email address',
        max_length=254,
        widget=forms.EmailInput(
            attrs={'placeholder': 'my.email@address.com'}
        )
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', None)
        # Check such an email exists
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cannot find an account with that email")
        teacher_filter = Teacher.objects.filter(user__user__email=email)
        # Check such an email is associated with a teacher
        if not teacher_filter.exists():
            raise forms.ValidationError("Cannot find an account with that email")
        self.username = teacher_filter[0].user.user.username
        return email

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Sends a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, 'text/html')

        email_message.send()

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None):
        """
        Generates a one-use only link for resetting password and sends to the
        user.
        """
        UserModel = get_user_model()
        active_users = UserModel._default_manager.filter(
            username=self.username, is_active=True)
        for user in active_users:
            # Make sure that no email is sent to a user that actually has
            # a password marked as unusable
            if not user.has_usable_password():
                continue
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            context = {
                'email': user.email,
                'domain': domain,
                'site_name': site_name,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
            }

            self.send_mail(subject_template_name, email_template_name,
                           context, from_email, user.email,
                           html_email_template_name=html_email_template_name)
