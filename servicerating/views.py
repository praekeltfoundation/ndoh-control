import csv
from django.http import HttpResponse
from servicerating.models import Response

def report_responses(request):

    qs = Response.objects.raw("SELECT servicerating_response.*, servicerating_extra.value AS clinic_code from servicerating_response INNER JOIN servicerating_extra ON servicerating_response.contact_id = servicerating_extra.contact_id WHERE servicerating_extra.key = 'clinic_code'")

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="servicerating_incl_clinic_code.csv"'

    writer = csv.writer(response)

    writer.writerow(["Contact", "Key", "Value", "Created At", "Updated At", "Clinic Code"])
    for obj in qs:
        writer.writerow([obj.contact, obj.key, obj.value, obj.created_at,
                        obj.updated_at, obj.clinic_code])

    return response
