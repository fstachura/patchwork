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
            '--projects',
            default=None,
            nargs='*',
            help='Names of projects to update labels for.'
        )

    def handle(self, *args, **options):
        query = Patch.objects.all()
        labels = {l.name:l for l in Label.objects.all()}

        if options['projects'] is not None:
            query = query.filter(project__name__in=options['projects'])

        count = query.count()

        for i, patch in enumerate(query.iterator()):
            parser = HeaderParser()
            headers = parser.parsestr(patch.headers)
            subject = headers['Subject']
            if subject is None:
                continue

            _, prefixes = clean_subject(subject)

            for prefix in prefixes:
                label = None

                if prefix in labels:
                    label = labels[prefix]
                else:
                    labels = Label.objects.filter(
                        name=prefix,
                        project__in=[patch.project, None],
                    ).all()

                    for l in labels:
                        label = l
                        # Prefer label created for this project
                        if l.project is not None:
                            break

                if label is not None:
                    patch.labels.add(label)
                    patch.save()

            if (i % 100) == 0:
                self.stdout.write('%06d/%06d\r' % (i, count), ending='')
                self.stdout.flush()
        self.stdout.write('\ndone')
