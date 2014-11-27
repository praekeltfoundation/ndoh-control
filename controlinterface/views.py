from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required(login_url='/controlinterface/login/')
def index(request):
    if (request.user.has_perm('controlinterface.view_dashboard_private') or
            request.user.has_perm('controlinterface.view_dashboard_summary')):
        return render(request,
                      'controlinterface/index.html')
    else:
        return render(request,
                      'controlinterface/index_nodash.html')

