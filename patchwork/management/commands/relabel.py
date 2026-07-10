from django.core.management.base import BaseCommand

import random
from email.parser import HeaderParser

from patchwork.models import Label, Patch, Series
from patchwork.parser import clean_subject


def parse_labels_from_header(global_labels, headers):
    parser = HeaderParser()
    headers = parser.parsestr(headers)
    subject = headers['Subject']
    if subject is None:
        return []

    _, prefixes = clean_subject(subject)

    result = []

    for prefix in prefixes:
        found_label = None

        for label in global_labels:
            if label.name == prefix:
                found_label = label
                # Prefer label created for this project
                if found_label.project is not None:
                    break

        if found_label is not None:
            result.append(found_label)

    return result


class Command(BaseCommand):
    help = (
        'Update labels for existing patches based on the subject line. '
        'Labels have to be created in the admin interface first.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'projects',
            metavar='PROJECT',
            nargs='*',
            help='list of project(s) to update labels for',
        )

    def handle(self, *args, **options):
        all_labels = list(Label.objects.all())

        print('relabeling series')

        series_query = Series.objects.all()

        if options['projects']:
            series_query = series_query.filter(
                project__name__in=options['projects']
            )

        series_count = series_query.count()

        for i, series in enumerate(series_query.iterator()):
            labels = None

            if series.cover_letter:
                labels = parse_labels_from_header(
                    all_labels, series.cover_letter.headers
                )
            else:
                patch = Patch.objects.filter(series=series, number=1).first()
                if patch is not None:
                    labels = parse_labels_from_header(
                        all_labels, patch.headers
                    )

            if labels is not None:
                series.labels.add(*labels)
                series.save()

            if (i % 100) == 0:
                self.stdout.write('%06d/%06d\r' % (i, series_count), ending='')
                self.stdout.flush()

        print('relabeling patches')

        patch_query = (
            Patch.objects.only('id', 'headers', 'series')
            .select_related('series')
            .prefetch_related('series__labels')
            .all()
        )

        if options['projects']:
            patch_query = patch_query.filter(
                project__name__in=options['projects']
            )

        patch_count = patch_query.count()

        for i, patch in enumerate(patch_query.iterator(chunk_size=1000)):
            labels = parse_labels_from_header(all_labels, patch.headers)

            patch.labels.add(*labels)

            if patch.series:
                patch.labels.add(*list(patch.series.labels.all()))

            patch.save()

            if (i % 100) == 0:
                self.stdout.write('%06d/%06d\r' % (i, patch_count), ending='')
                self.stdout.flush()
        self.stdout.write('\ndone')
