"""
Course certificate generation handler.

These methods check to see if a certificate can be generated (created if it does not already exist, or updated if it
exists but its state can be altered). If so, a celery task is launched to do the generation. If the certificate
cannot be generated, a message is logged and no further action is taken.

For now, these methods deal primarily with allowlist certificates, and are part of the V2 certificates revamp.
"""

import logging

import six
from edx_toggles.toggles import LegacyWaffleFlagNamespace

from lms.djangoapps.certificates.models import (
    CertificateStatuses,
    CertificateInvalidation,
    CertificateWhitelist,
    GeneratedCertificate
)
from lms.djangoapps.certificates.signals import CERTIFICATE_DELAY_SECONDS
from lms.djangoapps.certificates.tasks import generate_certificate
from openedx.core.djangoapps.certificates.api import auto_certificate_generation_enabled
from openedx.core.djangoapps.waffle_utils import CourseWaffleFlag

log = logging.getLogger(__name__)

WAFFLE_FLAG_NAMESPACE = LegacyWaffleFlagNamespace(name='certificates_revamp')

CERTIFICATES_USE_ALLOWLIST = CourseWaffleFlag(
    waffle_namespace=WAFFLE_FLAG_NAMESPACE,
    flag_name=u'use_allowlist',
    module_name=__name__,
)


def generate_allowlist_certificate_task(user, course_key):
    """
    Create a task to generate an allowlist certificate for this user in this course run.
    """
    if not can_generate_allowlist_certificate(user, course_key):
        log.info(
            u'Cannot generate an allowlist certificate for {user} : {course}'.format(user=user.id, course=course_key))
        return

    log.info(
        u'About to create an allowlist certificate task for {user} : {course}'.format(user=user.id, course=course_key))

    kwargs = {
        'student': six.text_type(user.id),
        'course_key': six.text_type(course_key),
        'allowlist_certificate': True
    }
    generate_certificate.apply_async(countdown=CERTIFICATE_DELAY_SECONDS, kwargs=kwargs)


def can_generate_allowlist_certificate(user, course_key):
    """
    Check if an allowlist certificate can be generated (created if it doesn't already exist, or updated if it does
    exist) for this user, in this course run.
    """
    if not auto_certificate_generation_enabled():
        # Automatic certificate generation is globally disabled
        log.info(u'Automatic certificate generation is globally disabled. Certificate cannot be generated.')
        return False

    if CertificateInvalidation.has_certificate_invalidation(user, course_key):
        # The invalidation list overrides the allowlist
        log.info(
            u'{user} : {course} is on the certificate invalidation list. Certificate cannot be generated.'.format(
                user=user.id,
                course=course_key
            ))
        return False

    if not _is_using_certificate_allowlist(course_key):
        # This course run is not using the allowlist feature
        log.info(
            u'{course} is not using the certificate allowlist. Certificate cannot be generated.'.format(
                course=course_key
            ))
        return False

    if CertificateWhitelist.objects.filter(user=user, course_id=course_key, whitelist=True).exists():
        log.info(u'{user} : {course} is on the certificate allowlist'.format(
            user=user.id,
            course=course_key
        ))
        cert = GeneratedCertificate.certificate_for_student(user, course_key)
        return _can_generate_allowlist_certificate_for_status(cert)

    log.info(u'{user} : {course} is not on the certificate allowlist. Certificate cannot be generated.'.format(
        user=user.id,
        course=course_key
    ))
    return False


def _is_using_certificate_allowlist(course_key):
    """
    Check if the course run is using the allowlist, aka V2 of certificate whitelisting
    """
    return CERTIFICATES_USE_ALLOWLIST.is_enabled(course_key)


def _can_generate_allowlist_certificate_for_status(cert):
    """
    Check if the user's certificate status allows certificate generation
    """
    if cert is None:
        return True

    if cert.status == CertificateStatuses.downloadable:
        log.info(u'Certificate with status {status} already exists for {user} : {course}, and is NOT eligible for '
                 u'allowlist generation. Certificate cannot be generated.'.format(status=cert.status,
                                                                                  user=cert.user.id,
                                                                                  course=cert.course_id
                                                                                  ))
        return False

    log.info(u'Certificate with status {status} already exists for {user} : {course}, and is eligible for '
             u'allowlist generation'.format(status=cert.status,
                                            user=cert.user.id,
                                            course=cert.course_id
                                            ))
    return True
