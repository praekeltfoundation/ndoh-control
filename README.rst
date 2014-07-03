ndoh-control
===============

Django application for MomConnect control interfaces.

Warning: Don't create a superuser on syncdb as TastyPie migrations have not yet occurred.

::

    $ virtualenv ve
    $ source ve/bin/activate
    (ve)$ pip install -r requirements.pip
    (ve)$ ./manage.py syncdb --migrate --noinput

