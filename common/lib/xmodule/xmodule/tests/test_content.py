"""Tests for contents"""
from StringIO import StringIO

import os
import unittest
import ddt
from PIL import Image
from mock import patch
from path import Path as path
from urllib import quote_plus

from xmodule.contentstore.content import StaticContent, StaticContentStream
from xmodule.contentstore.content import ContentStore
from xmodule.contentstore.django import contentstore
from opaque_keys.edx.locations import SlashSeparatedCourseKey, AssetLocation
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, check_mongo_calls
from xmodule.static_content import _write_js, _list_descriptors

SAMPLE_STRING = """
This is a sample string with more than 1024 bytes, the default STREAM_DATA_CHUNK_SIZE

Lorem Ipsum is simply dummy text of the printing and typesetting industry.
Lorem Ipsum has been the industry's standard dummy text ever since the 1500s,
when an unknown printer took a galley of type and scrambled it to make a type
specimen book. It has survived not only five centuries, but also the leap into
electronic typesetting, remaining essentially unchanged. It was popularised in
the 1960s with the release of Letraset sheets containing Lorem Ipsum passages,
nd more recently with desktop publishing software like Aldus PageMaker including
versions of Lorem Ipsum.

It is a long established fact that a reader will be distracted by the readable
content of a page when looking at its layout. The point of using Lorem Ipsum is
that it has a more-or-less normal distribution of letters, as opposed to using
'Content here, content here', making it look like readable English. Many desktop
ublishing packages and web page editors now use Lorem Ipsum as their default model
text, and a search for 'lorem ipsum' will uncover many web sites still in their infancy.
Various versions have evolved over the years, sometimes by accident, sometimes on purpose
injected humour and the like).

Lorem Ipsum is simply dummy text of the printing and typesetting industry.
Lorem Ipsum has been the industry's standard dummy text ever since the 1500s,
when an unknown printer took a galley of type and scrambled it to make a type
specimen book. It has survived not only five centuries, but also the leap into
electronic typesetting, remaining essentially unchanged. It was popularised in
the 1960s with the release of Letraset sheets containing Lorem Ipsum passages,
nd more recently with desktop publishing software like Aldus PageMaker including
versions of Lorem Ipsum.

It is a long established fact that a reader will be distracted by the readable
content of a page when looking at its layout. The point of using Lorem Ipsum is
that it has a more-or-less normal distribution of letters, as opposed to using
'Content here, content here', making it look like readable English. Many desktop
ublishing packages and web page editors now use Lorem Ipsum as their default model
text, and a search for 'lorem ipsum' will uncover many web sites still in their infancy.
Various versions have evolved over the years, sometimes by accident, sometimes on purpose
injected humour and the like).
"""


class Content(object):
    """
    A class with location and content_type members
    """
    def __init__(self, location, content_type):
        self.location = location
        self.content_type = content_type


class FakeGridFsItem(object):
    """
    This class provides the basic methods to get data from a GridFS item
    """
    def __init__(self, string_data):
        self.cursor = 0
        self.data = string_data
        self.length = len(string_data)

    def seek(self, position):
        """
        Set the cursor at "position"
        """
        self.cursor = position

    def read(self, chunk_size):
        """
        Read "chunk_size" bytes of data at position cursor and move the cursor
        """
        chunk = self.data[self.cursor:(self.cursor + chunk_size)]
        self.cursor += chunk_size
        return chunk


@ddt.ddt
class ContentTest(unittest.TestCase):
    def test_thumbnail_none(self):
        # We had a bug where a thumbnail location of None was getting transformed into a Location tuple, with
        # all elements being None. It is important that the location be just None for rendering.
        content = StaticContent('loc', 'name', 'content_type', 'data', None, None, None)
        self.assertIsNone(content.thumbnail_location)

        content = StaticContent('loc', 'name', 'content_type', 'data')
        self.assertIsNone(content.thumbnail_location)

    @ddt.data(
        (u"monsters__.jpg", u"monsters__.jpg"),
        (u"monsters__.png", u"monsters__-png.jpg"),
        (u"dots.in.name.jpg", u"dots.in.name.jpg"),
        (u"dots.in.name.png", u"dots.in.name-png.jpg"),
    )
    @ddt.unpack
    def test_generate_thumbnail_image(self, original_filename, thumbnail_filename):
        contentStore = ContentStore()
        content = Content(AssetLocation(u'mitX', u'800', u'ignore_run', u'asset', original_filename), None)
        (thumbnail_content, thumbnail_file_location) = contentStore.generate_thumbnail(content)
        self.assertIsNone(thumbnail_content)
        self.assertEqual(AssetLocation(u'mitX', u'800', u'ignore_run', u'thumbnail', thumbnail_filename), thumbnail_file_location)

    def test_compute_location(self):
        # We had a bug that __ got converted into a single _. Make sure that substitution of INVALID_CHARS (like space)
        # still happen.
        asset_location = StaticContent.compute_location(
            SlashSeparatedCourseKey('mitX', '400', 'ignore'), 'subs__1eo_jXvZnE .srt.sjson'
        )
        self.assertEqual(AssetLocation(u'mitX', u'400', u'ignore', u'asset', u'subs__1eo_jXvZnE_.srt.sjson', None), asset_location)

    def test_get_location_from_path(self):
        asset_location = StaticContent.get_location_from_path(u'/c4x/a/b/asset/images_course_image.jpg')
        self.assertEqual(
            AssetLocation(u'a', u'b', None, u'asset', u'images_course_image.jpg', None),
            asset_location
        )

    def test_static_content_stream_stream_data(self):
        """
        Test StaticContentStream stream_data function, asserts that we get all the bytes
        """
        data = SAMPLE_STRING
        item = FakeGridFsItem(data)
        static_content_stream = StaticContentStream('loc', 'name', 'type', item, length=item.length)

        total_length = 0
        stream = static_content_stream.stream_data()
        for chunck in stream:
            total_length += len(chunck)

        self.assertEqual(total_length, static_content_stream.length)

    def test_static_content_stream_stream_data_in_range(self):
        """
        Test StaticContentStream stream_data_in_range function,
        asserts that we get the requested number of bytes
        first_byte and last_byte are chosen to be simple but non trivial values
        and to have total_length > STREAM_DATA_CHUNK_SIZE (1024)
        """
        data = SAMPLE_STRING
        item = FakeGridFsItem(data)
        static_content_stream = StaticContentStream('loc', 'name', 'type', item, length=item.length)

        first_byte = 100
        last_byte = 1500

        total_length = 0
        stream = static_content_stream.stream_data_in_range(first_byte, last_byte)
        for chunck in stream:
            total_length += len(chunck)

        self.assertEqual(total_length, last_byte - first_byte + 1)

    def test_static_content_write_js(self):
        """
        Test that only one filename starts with 000.
        """
        output_root = path(u'common/static/xmodule/descriptors/js')
        js_file_paths = _write_js(output_root, _list_descriptors())
        js_file_paths = [file_path for file_path in js_file_paths if os.path.basename(file_path).startswith('000-')]
        self.assertEqual(len(js_file_paths), 1)
        self.assertIn("XModule.Descriptor = (function () {", open(js_file_paths[0]).read())


@ddt.ddt
class CanonicalContentTest(ModuleStoreTestCase):
    """
    Tests the generation of canonical asset URLs for different types
    of assets: c4x-style, opaque key style, locked, unlocked, CDN
    set, CDN not set, etc.
    """

    def setUp(self):
        self.courses = {}

        super(CanonicalContentTest, self).setUp()

        names_and_prefixes = [(ModuleStoreEnum.Type.split, 'split'), (ModuleStoreEnum.Type.mongo, 'old')]
        for store, prefix in names_and_prefixes:
            with self.store.default_store(store):
                self.courses[prefix] = CourseFactory.create(org='a', course='b', run=prefix)

                # Create an unlocked image.
                unlocked_image = Image.new('RGB', (512, 512), 'blue')
                unlocked_buf = StringIO()
                unlocked_image.save(unlocked_buf, format='png')
                unlocked_buf.seek(0)
                unlocked_name = '{}_unlock.png'.format(prefix)
                unlocked_asset_key = StaticContent.compute_location(self.courses[prefix].id, unlocked_name)
                unlocked_content = StaticContent(unlocked_asset_key, unlocked_name, 'image/png', unlocked_buf.buf)
                contentstore().save(unlocked_content)

                # Create a locked image.
                locked_image = Image.new('RGB', (512, 512), 'green')
                locked_buf = StringIO()
                locked_image.save(locked_buf, format='png')
                locked_buf.seek(0)
                locked_name = '{}_lock.png'.format(prefix)
                locked_asset_key = StaticContent.compute_location(self.courses[prefix].id, locked_name)
                locked_content = StaticContent(locked_asset_key, locked_name, 'image/png', locked_buf.buf, locked=True)
                contentstore().save(locked_content)

                # Create a thumbnail of the images.
                (_, thumb_loc) = contentstore().generate_thumbnail(unlocked_content, dimensions=(128, 128))
                (_, thumb_loc) = contentstore().generate_thumbnail(locked_content, dimensions=(128, 128))

                # Create an unlocked image in a subdirectory.
                subdir_unlocked_image = Image.new('RGB', (500, 500), 'red')
                subdir_unlocked_buf = StringIO()
                subdir_unlocked_image.save(subdir_unlocked_buf, format='png')
                subdir_unlocked_buf.seek(0)
                subdir_unlocked_name = 'special/{}_unlock.png'.format(prefix)
                subdir_unlocked_asset_key = StaticContent.compute_location(self.courses[prefix].id, subdir_unlocked_name)
                subdir_unlocked_content = StaticContent(subdir_unlocked_asset_key, subdir_unlocked_name, 'image/png', subdir_unlocked_buf)
                contentstore().save(subdir_unlocked_content)

                # Create a locked image in a subdirectory.
                subdir_locked_image = Image.new('RGB', (500, 500), 'red')
                subdir_locked_buf = StringIO()
                subdir_locked_image.save(subdir_locked_buf, format='png')
                subdir_locked_buf.seek(0)
                subdir_locked_name = 'special/{}_lock.png'.format(prefix)
                subdir_locked_asset_key = StaticContent.compute_location(self.courses[prefix].id, subdir_locked_name)
                subdir_locked_content = StaticContent(subdir_locked_asset_key, subdir_locked_name, 'image/png', subdir_locked_buf, locked=True)
                contentstore().save(subdir_locked_content)

    @ddt.data(
        # No leading slash.
        (None, u'{prefix}_unlock.png', u'/{asset_key}@{prefix}_unlock.png', 1),
        (None, u'{prefix}_lock.png', u'/{asset_key}@{prefix}_lock.png', 1),
        (u'dev', u'{prefix}_unlock.png', u'//dev/{asset_key}@{prefix}_unlock.png', 1),
        (u'dev', u'{prefix}_lock.png', u'/{asset_key}@{prefix}_lock.png', 1),
        # No leading slash with subdirectory.  This ensures we probably substitute slashes.
        (None, u'special/{prefix}_unlock.png', u'/{asset_key}@special_{prefix}_unlock.png', 1),
        (None, u'special/{prefix}_lock.png', u'/{asset_key}@special_{prefix}_lock.png', 1),
        (u'dev', u'special/{prefix}_unlock.png', u'//dev/{asset_key}@special_{prefix}_unlock.png', 1),
        (u'dev', u'special/{prefix}_lock.png', u'/{asset_key}@special_{prefix}_lock.png', 1),
        # Leading slash.
        (None, u'/{prefix}_unlock.png', u'/{asset_key}@{prefix}_unlock.png', 1),
        (None, u'/{prefix}_lock.png', u'/{asset_key}@{prefix}_lock.png', 1),
        (u'dev', u'/{prefix}_unlock.png', u'//dev/{asset_key}@{prefix}_unlock.png', 1),
        (u'dev', u'/{prefix}_lock.png', u'/{asset_key}@{prefix}_lock.png', 1),
        # Leading slash with subdirectory.  This ensures we probably substitute slashes.
        (None, u'/special/{prefix}_unlock.png', u'/{asset_key}@special_{prefix}_unlock.png', 1),
        (None, u'/special/{prefix}_lock.png', u'/{asset_key}@special_{prefix}_lock.png', 1),
        (u'dev', u'/special/{prefix}_unlock.png', u'//dev/{asset_key}@special_{prefix}_unlock.png', 1),
        (u'dev', u'/special/{prefix}_lock.png', u'/{asset_key}@special_{prefix}_lock.png', 1),
        # Static path.
        (None, u'/static/{prefix}_unlock.png', u'/{asset_key}@{prefix}_unlock.png', 1),
        (None, u'/static/{prefix}_lock.png', u'/{asset_key}@{prefix}_lock.png', 1),
        (u'dev', u'/static/{prefix}_unlock.png', u'//dev/{asset_key}@{prefix}_unlock.png', 1),
        (u'dev', u'/static/{prefix}_lock.png', u'/{asset_key}@{prefix}_lock.png', 1),
        # Static path with subdirectory.  This ensures we probably substitute slashes.
        (None, u'/static/special/{prefix}_unlock.png', u'/{asset_key}@special_{prefix}_unlock.png', 1),
        (None, u'/static/special/{prefix}_lock.png', u'/{asset_key}@special_{prefix}_lock.png', 1),
        (u'dev', u'/static/special/{prefix}_unlock.png', u'//dev/{asset_key}@special_{prefix}_unlock.png', 1),
        (u'dev', u'/static/special/{prefix}_lock.png', u'/{asset_key}@special_{prefix}_lock.png', 1),
        # Static path with query parameter.
        (
            None,
            u'/static/{prefix}_unlock.png?foo=/static/{prefix}_lock.png',
            u'/{asset_key}@{prefix}_unlock.png?foo={encoded_asset_key}{prefix}_lock.png',
            2
        ),
        (
            None,
            u'/static/{prefix}_lock.png?foo=/static/{prefix}_unlock.png',
            u'/{asset_key}@{prefix}_lock.png?foo={encoded_asset_key}{prefix}_unlock.png',
            2
        ),
        (
            u'dev',
            u'/static/{prefix}_unlock.png?foo=/static/{prefix}_lock.png',
            u'//dev/{asset_key}@{prefix}_unlock.png?foo={encoded_asset_key}{prefix}_lock.png',
            2
        ),
        (
            u'dev',
            u'/static/{prefix}_lock.png?foo=/static/{prefix}_unlock.png',
            u'/{asset_key}@{prefix}_lock.png?foo=%2F%2Fdev{encoded_asset_key}{prefix}_unlock.png',
            2
        ),
        # Already asset key.
        (None, u'/{asset_key}@{prefix}_unlock.png', u'/{asset_key}@{prefix}_unlock.png', 1),
        (None, u'/{asset_key}@{prefix}_lock.png', u'/{asset_key}@{prefix}_lock.png', 1),
        (u'dev', u'/{asset_key}@{prefix}_unlock.png', u'//dev/{asset_key}@{prefix}_unlock.png', 1),
        (u'dev', u'/{asset_key}@{prefix}_lock.png', u'/{asset_key}@{prefix}_lock.png', 1),
        # Old, c4x-style path.
        (None, u'/{c4x}/{prefix}_unlock.png', u'/{c4x}/{prefix}_unlock.png', 1),
        (None, u'/{c4x}/{prefix}_lock.png', u'/{c4x}/{prefix}_lock.png', 1),
        (u'dev', u'/{c4x}/{prefix}_unlock.png', u'/{c4x}/{prefix}_unlock.png', 1),
        (u'dev', u'/{c4x}/{prefix}_lock.png', u'/{c4x}/{prefix}_lock.png', 1),
        # Thumbnails.
        (None, u'/{th_key}@{prefix}_unlock-{th_ext}', u'/{th_key}@{prefix}_unlock-{th_ext}', 1),
        (None, u'/{th_key}@{prefix}_lock-{th_ext}', u'/{th_key}@{prefix}_lock-{th_ext}', 1),
        (u'dev', u'/{th_key}@{prefix}_unlock-{th_ext}', u'//dev/{th_key}@{prefix}_unlock-{th_ext}', 1),
        (u'dev', u'/{th_key}@{prefix}_lock-{th_ext}', u'//dev/{th_key}@{prefix}_lock-{th_ext}', 1),
    )
    @ddt.unpack
    def test_canonical_asset_path_with_new_style_assets(self, base_url, start, expected, mongo_calls):
        prefix = 'split'
        c4x = 'c4x/a/b/asset'
        asset_key = 'asset-v1:a+b+{}+type@asset+block'.format(prefix)
        encoded_asset_key = quote_plus('/asset-v1:a+b+{}+type@asset+block@'.format(prefix))
        th_key = 'asset-v1:a+b+{}+type@thumbnail+block'.format(prefix)
        th_ext = 'png-128x128.jpg'

        start = start.format(
            prefix=prefix,
            c4x=c4x,
            asset_key=asset_key,
            encoded_asset_key=encoded_asset_key,
            th_key=th_key,
            th_ext=th_ext
        )
        expected = expected.format(
            prefix=prefix,
            c4x=c4x,
            asset_key=asset_key,
            encoded_asset_key=encoded_asset_key,
            th_key=th_key,
            th_ext=th_ext
        )

        with check_mongo_calls(mongo_calls):
            asset_path = StaticContent.get_canonicalized_asset_path(self.courses[prefix].id, start, base_url)
            self.assertEqual(asset_path, expected)

    @ddt.data(
        # No leading slash.
        (None, u'{prefix}_unlock.png', u'/{c4x}/{prefix}_unlock.png'),
        (None, u'{prefix}_lock.png', u'/{c4x}/{prefix}_lock.png'),
        (u'dev', u'{prefix}_unlock.png', u'//dev/{c4x}/{prefix}_unlock.png'),
        (u'dev', u'{prefix}_lock.png', u'/{c4x}/{prefix}_lock.png'),
        # No leading slash with subdirectory.  This ensures we probably substitute slashes.
        (None, u'special/{prefix}_unlock.png', u'/{c4x}/special_{prefix}_unlock.png'),
        (None, u'special/{prefix}_lock.png', u'/{c4x}/special_{prefix}_lock.png'),
        (u'dev', u'special/{prefix}_unlock.png', u'//dev/{c4x}/special_{prefix}_unlock.png'),
        (u'dev', u'special/{prefix}_lock.png', u'/{c4x}/special_{prefix}_lock.png'),
        # Leading slash.
        (None, u'/{prefix}_unlock.png', u'/{c4x}/{prefix}_unlock.png'),
        (None, u'/{prefix}_lock.png', u'/{c4x}/{prefix}_lock.png'),
        (u'dev', u'/{prefix}_unlock.png', u'//dev/{c4x}/{prefix}_unlock.png'),
        (u'dev', u'/{prefix}_lock.png', u'/{c4x}/{prefix}_lock.png'),
        # Leading slash with subdirectory. T his ensures we probably substitute slashes.
        (None, u'/special/{prefix}_unlock.png', u'/{c4x}/special_{prefix}_unlock.png'),
        (None, u'/special/{prefix}_lock.png', u'/{c4x}/special_{prefix}_lock.png'),
        (u'dev', u'/special/{prefix}_unlock.png', u'//dev/{c4x}/special_{prefix}_unlock.png'),
        (u'dev', u'/special/{prefix}_lock.png', u'/{c4x}/special_{prefix}_lock.png'),
        # Static path.
        (None, u'/static/{prefix}_unlock.png', u'/{c4x}/{prefix}_unlock.png'),
        (None, u'/static/{prefix}_lock.png', u'/{c4x}/{prefix}_lock.png'),
        (u'dev', u'/static/{prefix}_unlock.png', u'//dev/{c4x}/{prefix}_unlock.png'),
        (u'dev', u'/static/{prefix}_lock.png', u'/{c4x}/{prefix}_lock.png'),
        # Static path with subdirectory.  This ensures we probably substitute slashes.
        (None, u'/static/special/{prefix}_unlock.png', u'/{c4x}/special_{prefix}_unlock.png'),
        (None, u'/static/special/{prefix}_lock.png', u'/{c4x}/special_{prefix}_lock.png'),
        (u'dev', u'/static/special/{prefix}_unlock.png', u'//dev/{c4x}/special_{prefix}_unlock.png'),
        (u'dev', u'/static/special/{prefix}_lock.png', u'/{c4x}/special_{prefix}_lock.png'),
        # Old, c4x-style path.
        (None, u'/{c4x}/{prefix}_unlock.png', u'/{c4x}/{prefix}_unlock.png'),
        (None, u'/{c4x}/{prefix}_lock.png', u'/{c4x}/{prefix}_lock.png'),
        (u'dev', u'/{c4x}/{prefix}_unlock.png', u'//dev/{c4x}/{prefix}_unlock.png'),
        (u'dev', u'/{c4x}/{prefix}_lock.png', u'/{c4x}/{prefix}_lock.png'),
    )
    @ddt.unpack
    def test_canonical_asset_path_with_c4x_style_assets(self, base_url, start, expected):
        prefix = 'old'
        c4x_block = 'c4x/a/b/asset'

        start = start.format(prefix=prefix, c4x=c4x_block)
        expected = expected.format(prefix=prefix, c4x=c4x_block)

        with check_mongo_calls(1):
            asset_path = StaticContent.get_canonicalized_asset_path(self.courses[prefix].id, start, base_url)
            self.assertEqual(asset_path, expected)
