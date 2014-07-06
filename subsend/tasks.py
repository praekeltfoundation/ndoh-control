from celery import task


@task()
def process_message_queue():
    return True
