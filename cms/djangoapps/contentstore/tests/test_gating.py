"""
Unit tests for the gating feature in Studio
"""
from mock import patch
from django.test import TestCase
from contentstore.signals import handle_item_deleted


class TestHandleItemDeleted(TestCase):
    """
    Test case for handle_score_changed django signal handler
    """
    def setUp(self):
        super(TestHandleItemDeleted, self).setUp()
        self.test_usage_key = 'i4x://the/content/key/12345678'

    @patch('contentstore.signals.gating_api.remove_prerequisite')
    def test_handle_item_deleted(self, mock_remove):
        """ Test evaluate_prerequisite is called when course.enable_subsection_gating is True """
        handle_item_deleted(usage_key=self.test_usage_key)
        mock_remove.assert_called_with(self.test_usage_key)
