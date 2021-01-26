"""
Tests for the cert_allowlist command
"""

import pytest
from django.core.management import CommandError, call_command
from edx_toggles.toggles.testutils import override_waffle_flag
from waffle.testutils import override_switch
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

from common.djangoapps.student.tests.factories import CourseEnrollmentFactory, UserFactory
from lms.djangoapps.certificates.generation_handler import CERTIFICATES_USE_ALLOWLIST
from lms.djangoapps.certificates.models import CertificateWhitelist, GeneratedCertificate
from lms.djangoapps.certificates.tests.factories import CertificateWhitelistFactory
from openedx.core.djangoapps.certificates.config import waffle


class CertAllowlistGenerationTests(ModuleStoreTestCase):
    """
    Tests for the cert_allowlist_generation management command
    """

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.course_run = CourseFactory()
        self.enrollment = CourseEnrollmentFactory(
            user=self.user,
            course_id=self.course_run.id,
            is_active=True,
            mode="verified",
        )

        self.user2 = UserFactory()
        self.enrollment2 = CourseEnrollmentFactory(
            user=self.user2,
            course_id=self.course_run.id,
            is_active=True,
            mode="verified",
        )

    def test_command_with_missing_param(self):
        """
        Verify command with a missing param
        """
        with pytest.raises(CommandError, match="Error: the following arguments are required: -c/--course-key"):
            call_command("cert_allowlist_generation", "--u", self.user.username)

    @override_switch(waffle.WAFFLE_NAMESPACE + '.' + waffle.AUTO_CERTIFICATE_GENERATION, True)
    @override_waffle_flag(CERTIFICATES_USE_ALLOWLIST, active=True)
    def test_successful_generation(self):
        """
        Test generation for 1 user
        """
        # Whitelist student
        CertificateWhitelistFactory.create(course_id=self.course_run.id, user=self.user)

        allowlist = CertificateWhitelist.objects.filter(user=self.user, course_id=self.course_run.id)
        self.assertEqual(len(allowlist), 1)

        call_command("cert_allowlist_generation", "--u", self.user.username, "--c", self.course_run.id)

    @override_switch(waffle.WAFFLE_NAMESPACE + '.' + waffle.AUTO_CERTIFICATE_GENERATION, True)
    @override_waffle_flag(CERTIFICATES_USE_ALLOWLIST, active=True)
    def test_successful_generation_multiple_users(self):
        """
        Test generation for multiple user
        """
        # Whitelist students
        CertificateWhitelistFactory.create(course_id=self.course_run.id, user=self.user)
        CertificateWhitelistFactory.create(course_id=self.course_run.id, user=self.user2)

        allowlist = CertificateWhitelist.objects.filter(user=self.user, course_id=self.course_run.id)
        self.assertEqual(len(allowlist), 1)
        allowlist = CertificateWhitelist.objects.filter(user=self.user2, course_id=self.course_run.id)
        self.assertEqual(len(allowlist), 1)

        call_command("cert_allowlist_generation",
                     "--u",
                     self.user.username,
                     self.user2.email,
                     "invalid_user",
                     " ",
                     "--c",
                     self.course_run.id)
