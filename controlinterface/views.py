from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import requests

@login_required(login_url='/controlinterface/login/')
def index(request):
    if (request.user.has_perm('controlinterface.view_dashboard_private') or
            request.user.has_perm('controlinterface.view_dashboard_summary')):
        return render(request,
                      'controlinterface/index.html')
    else:
        return render(request,
                      'controlinterface/index_nodash.html')


@login_required(login_url='/controlinterface/login/')
def subscriptions(request):
    if (request.user.has_perm('controlinterface.view_dashboard_private') or
            request.user.has_perm('controlinterface.view_dashboard_summary')):

        url = 'http://localhost:8000/api/v1/subscription/'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'ApiKey george:dGVzdDp0ZXN0'
        }
        params = {
            'to_addr': '+27727372369'
        }

        try:
            subs = requests.get(url, headers=headers, params=params)

            subscriptions = []

            for obj in subs.json()[u'objects']:
                subscription = {
                    'subscriber': obj[u'to_addr'],
                    'message_set': obj[u'message_set'][u'short_name'],
                    'next_message': obj[u'next_sequence_number'],
                    'language': obj[u'lang'],
                    'active': obj[u'active'],
                    'completed': obj[u'completed'],
                    'schedule': obj[u'schedule'][u'name'],
                }
                subscriptions.append(subscription)

            context = {
                'subscriptions': subscriptions
            }

            return render(request,
                          'controlinterface/subscriptions.html',
                          context)
        except:
            return render(request,
                          'controlinterface/index_nodash.html')
