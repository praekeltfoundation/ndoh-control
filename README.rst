ndoh-control
===============

Django application for MomConnect control interfaces.

Warning: Don't create a superuser on syncdb as TastyPie migrations have not yet occurred.

::

    $ virtualenv ve
    $ source ve/bin/activate
    (ve)$ pip install -r requirements.txt
    (ve)$ ./manage.py syncdb --migrate --noinput


Metrics produced:
Note all metrics are prepended by their <env>, e.g. 'qa.'

NurseConnect Metrics

* sum.nurseconnect_auto (SUM metric number of subscription completions)
* sum.nurseconnect.sms.outbound (SUM metric number of nurseconnect SMSs sent)
* sum.nurseconnect.<category>.sms.outbound (SUM metric number SMSs sent per category)
* sum.nurseconnect.unique.clinics (SUM metric number of unique clinics nurses have registered)
