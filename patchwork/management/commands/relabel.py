from django.core.management.base import BaseCommand

import random
from email.parser import HeaderParser

from patchwork.models import Label, Patch
from patchwork.parser import clean_subject


class Command(BaseCommand):
    help = 'Update labels for existing patches based on the subject line. ' \
           'Labels have to be created in the admin interface first.'

    def add_arguments(self, parser):
        parser.add_argument(
            'projects',
            metavar='PROJECT',
            nargs='*',
            help='list of project(s) to update labels for'
        )

    def handle(self, *args, **options):
        query = Patch.objects.all().only('id', 'headers', 'project_id')
        labels = {(l.name, l.project_id):l for l in Label.objects.all()}
        labels_to_add = []

        if options['projects']:
            query = query.filter(project__name__in=options['projects'])

        count = query.count()

        for i, patch in enumerate(query.iterator(chunk_size=1000)):
            parser = HeaderParser()
            headers = parser.parsestr(patch.headers)
            subject = headers['Subject']
            if subject is None:
                continue

            _, prefixes = clean_subject(subject)

            for prefix in set(prefixes):
                label = labels.get((prefix, patch.project_id))

                if label is None:
                    label = labels.get((prefix, None))

                if label is not None:
                    labels_to_add.append(Patch.labels.through(patch_id=patch.id, label_id=label.id))

            if (i % 100) == 0:
                self.stdout.write('%06d/%06d\r' % (i, count), ending='')
                self.stdout.flush()

            if len(labels_to_add) >= 1000:
                Patch.labels.through.objects.bulk_create(labels_to_add)
                labels_to_add = []

        if len(labels_to_add) > 0:
            Patch.labels.through.objects.bulk_create(labels_to_add)
            labels_to_add = []

        self.stdout.write('\ndone')

