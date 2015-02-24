import math
import csv

from django.shortcuts import render, render_to_response, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template import RequestContext
from django.contrib import messages
from django.core.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
from django import forms

import control.settings as settings

from models import Dashboard, UserDashboard
from subscription.models import (Message,
                                 Subscription,
                                 MessageSet)
from servicerating.models import Response
from subscription.forms import (MessageFindForm,
                                MessageUpdateForm,
                                MessageConfirmForm,
                                SubscriptionFindForm,
                                SubscriptionConfirmCancelForm,
                                SubscriptionConfirmBabyForm,
                                SubscriptionCancelForm,
                                SubscriptionBabyForm,
                                )


def get_user_dashboards(request):
    if (request.user.has_perm('controlinterface.view_dashboard_private') or
            request.user.has_perm('controlinterface.view_dashboard_summary')):
        user_dashboards = UserDashboard.objects.get(user=request.user)
        dashboards = {}
        for dash in user_dashboards.dashboards.all():
            dashboards[dash.id] = dash.name
        return {"dashboards": dashboards}
    else:
        return {"dashboards": {}}


@login_required(login_url='/controlinterface/login/')
def index(request):
    if (request.user.has_perm('controlinterface.view_dashboard_private') or
            request.user.has_perm('controlinterface.view_dashboard_summary')):

        user_dashboards = UserDashboard.objects.get(user=request.user)
        return redirect('dashboard',
                        dashboard_id=user_dashboards.default_dashboard.id)
    else:
        return render(request,
                      'controlinterface/index_nodash.html')


@login_required(login_url='/controlinterface/login/')
def dashboard(request, dashboard_id):
    context = get_user_dashboards(request)
    if (request.user.has_perm('controlinterface.view_dashboard_private') or
            request.user.has_perm('controlinterface.view_dashboard_summary')):

        try:
            access = Dashboard.objects.get(
                id=dashboard_id).dashboards.filter(
                user=request.user).count()
            if access == 1:
                dashboard = Dashboard.objects.get(id=dashboard_id)
                dashboard_widgets = dashboard.widgets.all()

                widgets = {}
                for widget in dashboard_widgets:
                    widgets[widget.id] = {
                        "config": widget,
                        "data": widget.data.all()
                    }

                context.update({
                    "widgets": widgets,
                    "dashboard_api_key": settings.DASHBOARD_API_KEY
                })

                return render(request,
                              'controlinterface/index.html',
                              context)
            else:
                return render(request,
                              'controlinterface/index_notdashallowed.html')
        except ObjectDoesNotExist:
            # User tried to access a dashboard they're not allowed to
            return render(request,
                          'controlinterface/index_notdashallowed.html')
    else:
        return render(request,
                      'controlinterface/index_nodash.html')


@login_required(login_url='/controlinterface/login/')
def message_edit(request):
    context = get_user_dashboards(request)
    if request.method == "POST" and request.POST["messageaction"] == "find":
        # Locate the record

        form = MessageFindForm(request.POST)
        if form.is_valid():
            try:
                message = Message.objects.get(
                    message_set_id=form.cleaned_data['message_set'],
                    sequence_number=form.cleaned_data['sequence_number'],
                    lang=form.cleaned_data['lang'])
                updateform = MessageUpdateForm()
                updateform.fields["message_id"].initial = message.id
                updateform.fields["content"].initial = message.content
                context.update({
                    "updateform": updateform,
                    "contentlength": len(message.content)
                })
                context.update(csrf(request))

            except ObjectDoesNotExist:
                messages.error(request,
                               "Message could not be found",
                               extra_tags="danger")
                context = {"form": form}
                context.update(csrf(request))
    elif request.method == "POST" and \
            request.POST["messageaction"] == "update":
        # Update the record
        updateform = MessageUpdateForm(request.POST)
        if updateform.is_valid():
            if len(updateform.cleaned_data['content']) > 160:
                messages.error(request,
                               "SMS messages cannot be longer than 160 "
                               "characters. Please edit this message to be "
                               "under 160 characters in order to save your "
                               "changes",
                               extra_tags="danger")
                context.update({"updateform": updateform})
            else:
                confirmform = MessageConfirmForm()
                confirmform.fields[
                    "message_id"].initial = updateform.cleaned_data['message_id']
                confirmform.fields[
                    "content"].initial = updateform.cleaned_data['content']
                context.update({"confirmform": confirmform,
                                "content": updateform.cleaned_data['content']})
                context.update(csrf(request))
        else:
            # Errors are handled by bootstrap form
            context.update({"updateform": updateform})
        context.update(csrf(request))
    elif request.method == "POST" and \
            request.POST["messageaction"] == "confirm":
        # Update the record
        confirmform = MessageConfirmForm(request.POST)
        if confirmform.is_valid():
            try:
                message = Message.objects.get(
                    pk=confirmform.cleaned_data['message_id'])
                message.content = confirmform.cleaned_data['content']
                message.save()
                messages.success(request,
                                 "Message has been updated",
                                 extra_tags="success")
                # Load the blank find form again
                form = MessageFindForm()
                context.update({"form": form})
                context.update(csrf(request))
            except ObjectDoesNotExist:
                messages.error(request,
                               "Message could not be found",
                               extra_tags="danger")
                context.update({"confirmform": confirmform})
                context.update(csrf(request))

        else:
            # Errors are handled by bootstrap form
            context.update({"confirmform": confirmform})
        context.update(csrf(request))
    else:
        form = MessageFindForm()
        context.update({"form": form})
        context.update(csrf(request))

    return render_to_response("controlinterface/messages.html",
                              context,
                              context_instance=RequestContext(request))


@login_required(login_url='/controlinterface/login/')
def subscription_edit(request):
    context = get_user_dashboards(request)
    if request.method == "POST" and request.POST["subaction"] == "find":
        # Locate the record
        form = SubscriptionFindForm(request.POST)
        if form.is_valid():
            subscriptions = Subscription.objects.filter(
                to_addr=form.cleaned_data['msisdn'])
            if subscriptions.count() == 0:
                messages.error(request,
                               "Subscriber could not be found",
                               extra_tags="danger")
                context.update({"form": form})
                context.update(csrf(request))
            else:
                confirmcancelform = SubscriptionConfirmCancelForm()
                confirmcancelform.fields[
                    "msisdn"].initial = form.cleaned_data['msisdn']
                confirmbabyform = SubscriptionConfirmBabyForm()
                confirmbabyform.fields["msisdn"].initial = \
                    form.cleaned_data['msisdn']
                confirmbabyform.fields["existing_id"].initial = \
                    subscriptions[0].id
                context.update({
                    "subscriptions": subscriptions,
                    "confirmcancelform": confirmcancelform,
                    "confirmbabyform": confirmbabyform,
                })
                context.update(csrf(request))
    elif request.method == "POST" and \
            request.POST["subaction"] == "confirmcancel":
        # Confirm before update the record

        confirmcancelform = SubscriptionConfirmCancelForm(request.POST)
        if confirmcancelform.is_valid():
            cancelform = SubscriptionCancelForm()
            cancelform.fields["msisdn"].initial = \
                confirmcancelform.cleaned_data['msisdn']
            form = SubscriptionFindForm()
            form.fields["msisdn"].widget = forms.HiddenInput()
            form.fields["msisdn"].initial = \
                confirmcancelform.cleaned_data['msisdn']
            context.update({
                "cancelform": cancelform,
                "form": form
            })
            context.update(csrf(request))
    elif request.method == "POST" and \
            request.POST["subaction"] == "confirmbaby":
        # Confirm before update the record

        confirmbabyform = SubscriptionConfirmBabyForm(request.POST)
        if confirmbabyform.is_valid():
            babyform = SubscriptionBabyForm()
            babyform.fields["msisdn"].initial = \
                confirmbabyform.cleaned_data['msisdn']
            babyform.fields["existing_id"].initial = \
                confirmbabyform.cleaned_data['existing_id']
            form = SubscriptionFindForm()
            form.fields["msisdn"].widget = forms.HiddenInput()
            form.fields["msisdn"].initial = \
                confirmbabyform.cleaned_data['msisdn']
            context.update({
                "babyform": babyform,
                "form": form
            })
            context.update(csrf(request))
    elif request.method == "POST" and \
            request.POST["subaction"] == "cancel":
        # Update the record
        cancelform = SubscriptionCancelForm(request.POST)
        if cancelform.is_valid():
            subscriptions = Subscription.objects.filter(
                to_addr=cancelform.cleaned_data['msisdn']).update(
                active=False)
            messages.success(request,
                             "All subscriptions for %s have been cancelled" %
                             cancelform.cleaned_data['msisdn'],
                             extra_tags="success")
            form = SubscriptionFindForm()
            form.fields[
                "msisdn"].initial = cancelform.cleaned_data['msisdn']
            context.update({"form": form})
            context.update(csrf(request))
    elif request.method == "POST" and \
            request.POST["subaction"] == "baby":
        # Update the record
        babyform = SubscriptionBabyForm(request.POST)
        if babyform.is_valid():
            # deactivate all
            subscriptions = Subscription.objects.filter(
                to_addr=babyform.cleaned_data['msisdn']).update(
                active=False)
            # load existing to clone
            subscription = Subscription.objects.get(
                pk=babyform.cleaned_data['existing_id'])
            subscription.pk = None
            subscription.process_status = 0  # Ready
            subscription.active = True
            subscription.completed = False
            subscription.next_sequence_number = 1
            newsub = subscription
            baby_message_set = MessageSet.objects.get(short_name="baby1")
            newsub.message_set = baby_message_set
            newsub.schedule = (
                baby_message_set.default_schedule)
            newsub.save()

            messages.success(request,
                             "All active subscriptions for %s have been "
                             "cancelled and baby subscription added" %
                             babyform.cleaned_data['msisdn'],
                             extra_tags="success")
            # Load the blank find form again
            form = SubscriptionFindForm()
            form.fields[
                "msisdn"].initial = babyform.cleaned_data['msisdn']
            context.update({"form": form})
        context.update(csrf(request))
    else:
        form = SubscriptionFindForm()
        context.update({"form": form})
        context.update(csrf(request))

    return render_to_response("controlinterface/subscription.html",
                              context,
                              context_instance=RequestContext(request))


def empty_response_map():
    response_map = {
        'question_1_friendliness': {
            'very-satisfied': 0,
            'satisfied': 0,
            'not-satisfied': 0,
            'very-unsatisfied': 0
        },
        'question_2_waiting_times_feel': {
            'very-satisfied': 0,
            'satisfied': 0,
            'not-satisfied': 0,
            'very-unsatisfied': 0
        },
        'question_3_waiting_times_length': {
            'less-than-an-hour': 0,
            'between-1-and-3-hours': 0,
            'more-than-4-hours': 0,
            'all-day': 0
        },
        'question_4_cleanliness': {
            'very-satisfied': 0,
            'satisfied': 0,
            'not-satisfied': 0,
            'very-unsatisfied': 0
        },
        'question_5_privacy': {
            'very-satisfied': 0,
            'satisfied': 0,
            'not-satisfied': 0,
            'very-unsatisfied': 0
        }
    }
    return response_map


@login_required(login_url='/controlinterface/login/')
def servicerating(request):
    context = get_user_dashboards(request)
    if (request.user.has_perm('controlinterface.view_dashboard_private') or
            request.user.has_perm('controlinterface.view_dashboard_summary')):

        averages = {}

        all_responses = Response.objects.all()
        num_questions = 5.0
        total_responses = 0

        response_map = empty_response_map()

        for response in all_responses:
            total_responses += 1
            response_map[response.key][response.value] += 1

        num_ratings = math.ceil(total_responses / num_questions)

        averages_questions = [
            'question_1_friendliness',
            'question_2_waiting_times_feel',
            'question_4_cleanliness',
            'question_5_privacy'
        ]

        question_3_map = response_map['question_3_waiting_times_length']
        waiting_times = {
            'less_than_an_hour': round(
                (question_3_map['less-than-an-hour'] / num_ratings * 100),
                1),
            'between_1_and_3_hours': round(
                (question_3_map['between-1-and-3-hours'] / num_ratings * 100),
                1),
            'more_than_4_hours': round(
                (question_3_map['more-than-4-hours'] / num_ratings * 100),
                1),
            'all_day': round(
                (question_3_map['all-day'] / num_ratings * 100),
                1)
        }

        for question in averages_questions:
            averages[question] = round((
                (response_map[question]['very-satisfied'] * 4) +
                (response_map[question]['satisfied'] * 3) +
                (response_map[question]['not-satisfied'] * 2) +
                (response_map[question]['very-unsatisfied'] * 1)
            ) / num_ratings, 1)

        context.update({
            'averages': averages,
            'waiting_times': waiting_times
        })

        return render(request, 'controlinterface/serviceratings.html', context)


@login_required(login_url='/controlinterface/login/')
def servicerating_report(request):
    if (request.user.has_perm('controlinterface.view_dashboard_private') or
            request.user.has_perm('controlinterface.view_dashboard_summary')):

        qs = Response.objects.raw("""
            SELECT servicerating_response.*, servicerating_extra.value
            AS clinic_code from servicerating_response
            INNER JOIN servicerating_extra ON
            servicerating_response.contact_id = servicerating_extra.contact_id
            WHERE servicerating_extra.key = 'clinic_code'""")

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="servicerating_incl_clinic_code.csv"')

        writer = csv.writer(response)

        writer.writerow(["Rating ID", "Contact ID", "Key", "Value",
                         "Created At", "Updated At", "Clinic Code"])
        for obj in qs:
            writer.writerow([obj.id, obj.contact_id, obj.key, obj.value,
                             obj.created_at, obj.updated_at, obj.clinic_code])

        return response
