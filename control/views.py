from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def index(request):
    return render(request,
                  'control/index.html')

@login_required
def control_index(request):
    return render(request, 'custom_admin/demo/index.html')
