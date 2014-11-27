from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from models import Dashboard


@login_required(login_url='/controlinterface/login/')
def index(request):
    if (request.user.has_perm('controlinterface.view_dashboard_private') or
            request.user.has_perm('controlinterface.view_dashboard_summary')):

        dashboard = Dashboard.objects.get(pk=1)

        widgets = dashboard.widgets.all()

        widget_data = {}

        for widget in widgets:
            widget_data[widget.id] = widget.data.all()

        context = {
            "widgets": dashboard.widgets.all(),
            "widget_data": widget_data
        }

        return render(request,
                      'controlinterface/index.html',
                      context)
    else:
        return render(request,
                      'controlinterface/index_nodash.html')

