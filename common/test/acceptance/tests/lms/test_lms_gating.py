# -*- coding: utf-8 -*-
"""
End-to-end tests for the gating feature.
"""
from ..helpers import UniqueCourseTest
from ...pages.studio.auto_auth import AutoAuthPage
from ...pages.studio.overview import CourseOutlinePage
from ...pages.lms.courseware import CoursewarePage
from ...pages.common.logout import LogoutPage
from ...fixtures.course import CourseFixture, XBlockFixtureDesc


class GatingTest(UniqueCourseTest):
    """
    Test gating feature in LMS.
    """
    USERNAME = "STUDENT_TESTER"
    EMAIL = "student101@example.com"

    def setUp(self):
        super(GatingTest, self).setUp()

        self.logout_page = LogoutPage(self.browser)
        self.courseware_page = CoursewarePage(self.browser, self.course_id)
        self.course_outline = CourseOutlinePage(
            self.browser,
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run']
        )

        # Install a course with sections/problems
        course_fixture = CourseFixture(
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run'],
            self.course_info['display_name']
        )
        course_fixture.add_advanced_settings({
            "enable_subsection_gating": {"value": "true"}
        })

        course_fixture.add_children(
            XBlockFixtureDesc('chapter', 'Test Section 1').add_children(
                XBlockFixtureDesc('sequential', 'Test Subsection 1').add_children(
                    XBlockFixtureDesc('problem', 'Test Problem 1')
                ),
                XBlockFixtureDesc('sequential', 'Test Subsection 2').add_children(
                    XBlockFixtureDesc('problem', 'Test Problem 2')
                )
            )
        ).install()

    def _auto_auth(self, username, email, staff):
        """
        Logout and login with given credentials.
        """
        self.logout_page.visit()
        AutoAuthPage(self.browser, username=username, email=email,
                     course_id=self.course_id, staff=staff).visit()

    def _setup_prereq(self):
        """
        Make the first subsection a prerequisite
        """
        # Login as staff
        self._auto_auth("STAFF_TESTER", "staff101@example.com", True)

        # Make the first subsection a prerequisite
        self.course_outline.visit()
        self.course_outline.open_subsection_settings_dialog(0)
        self.course_outline.select_access_tab()
        self.course_outline.make_gating_prerequisite()

    def _setup_gated_subsection(self):
        """
        Gate the second subsection on the first subsection
        """
        # Login as staff
        self._auto_auth("STAFF_TESTER", "staff101@example.com", True)

        # Gate the second subsection based on the score achieved in the first subsection
        self.course_outline.visit()
        self.course_outline.open_subsection_settings_dialog(1)
        self.course_outline.select_access_tab()
        self.course_outline.add_prerequisite_to_subsection("80")

    def test_subsection_gating_in_studio(self):
        """
        Given that I am a staff member
        When I visit the course outline page in studio.
        And open the subsection edit dialog
        Then I can view all settings related to Gating
        And update those settings to gate a subsection
        """
        self._setup_prereq()

        # Assert settings are displayed correctly for a prerequisite subsection
        self.course_outline.visit()
        self.course_outline.open_subsection_settings_dialog(0)
        self.course_outline.select_access_tab()
        self.assertTrue(self.course_outline.gating_prerequisite_checkbox_is_visible())
        self.assertTrue(self.course_outline.gating_prerequisite_checkbox_is_checked())
        self.assertFalse(self.course_outline.gating_prerequisites_dropdown_is_visible())
        self.assertFalse(self.course_outline.gating_prerequisite_min_score_is_visible())

        self._setup_gated_subsection()

        # Assert settings are displayed correctly for a gated subsection
        self.course_outline.visit()
        self.course_outline.open_subsection_settings_dialog(1)
        self.course_outline.select_access_tab()
        self.assertTrue(self.course_outline.gating_prerequisite_checkbox_is_visible())
        self.assertTrue(self.course_outline.gating_prerequisites_dropdown_is_visible())
        self.assertTrue(self.course_outline.gating_prerequisite_min_score_is_visible())

    def test_gated_subsection_in_lms(self):
        """
        Given that I am a student
        When I visit the LMS Courseware
        Then I cannot see a gated subsection
        """
        self._setup_prereq()
        self._setup_gated_subsection()

        self._auto_auth(self.USERNAME, self.EMAIL, False)

        self.courseware_page.visit()
        self.assertEqual(self.courseware_page.num_subsections, 1)
