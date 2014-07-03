from celery import task
import csv
from subscription.models import Message
from django.db import IntegrityError, transaction
import logging
logger = logging.getLogger(__name__)


@task()
# @transaction.atomic
def ingest_csv(csv_data, message_set):
    """ Expecting data in the following format:
    message_id,en,safe,af,safe,zu,safe,xh,safe,ve,safe,tn,safe,ts,safe,ss,safe,st,safe,nso,safe,nr,safe
    """
    records = csv.DictReader(csv_data)
    for line in records:
        for key in line.iterkeys():
            # Ignore non-content keys and empty keys
            if key not in ["message_id", "safe"] and line[key] != "":
                try:
                    with transaction.atomic():
                        message = Message()
                        message.message_set = message_set
                        message.sequence_number = line["message_id"]
                        message.lang = key
                        message.content = line[key]
                        message.save()
                except (IntegrityError, ValueError) as e:
                    message = None
                    # crappy CSV data
                    logger.error(e)
