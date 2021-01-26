"""
Management command to generate allowlist certificates for one or more users in a given course run.
"""

import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.certificates.generation_handler import generate_allowlist_certificate_task

log = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to generate allowlist certificates for one or more users in a given course run.
    """

    help = """
    Generate allowlist certificates for one or more users in a given course run.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '-u', '--user',
            nargs="+",
            metavar='USER',
            dest='user',
            required=False,
            help='user or comma-separated list of users for whom to generate allowlist certificates'
        )
        parser.add_argument(
            '-c', '--course-key',
            metavar='COURSE_KEY',
            dest='course_key',
            required=True,
            help="course run key"
        )

    def handle(self, *args, **options):
        # Parse the serialized course key into a CourseKey
        course_key = options['course_key']
        if not course_key:
            raise CommandError("You must specify a course-key")

        course_key = CourseKey.from_string(course_key)

        # TODO: handle for all users in whitelist for this courserun
        # Loop over each user, and ask that a cert be generated for them
        users_str = options['user']
        for user_identifier in users_str:
            user = _get_user_from_identifier(user_identifier)
            if user is not None:
                generate_allowlist_certificate_task(user, course_key)


def _get_user_from_identifier(identifier):
    """
    Using the string identifier, fetch the relevant user object from database
    """
    try:
        if '@' in identifier:
            user = User.objects.get(email=identifier)
        else:
            user = User.objects.get(username=identifier)
        return user
    except User.DoesNotExist:
        log.warning(u'{user} could not be found'.format(user=identifier))
        return None
