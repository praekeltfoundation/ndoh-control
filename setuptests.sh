#!/bin/bash
psql -c 'create database control;' -U postgres
echo "DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql_psycopg2', 'NAME': 'control', 'USER': 'postgres', 'PASSWORD': '', 'HOST': 'localhost', 'PORT': ''}}" > control/local_settings.py