# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016 Roman Yepishev <rye@keypressure.com>
#
# This file is part of duplicity.
#
# Duplicity is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# Duplicity is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with duplicity; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

u"""MediaFire Duplicity Backend"""

from builtins import str

import os

import duplicity.backend
from duplicity import util
from duplicity.errors import BackendException

DUPLICITY_APP_ID = u'45593'


class MediafireBackend(duplicity.backend.Backend):
    u"""Use this backend when saving to MediaFire

    URLs look like mf:/root/folder.
    """
    def __init__(self, parsed_url):
        try:
            import mediafire.client
        except ImportError as e:
            raise BackendException(u"""\
Mediafire backend requires the mediafire library.
Exception: %s""" % str(e))

        duplicity.backend.Backend.__init__(self, parsed_url)

        mediafire_email = parsed_url.username
        mediafire_password = self.get_password()

        self._file_res = mediafire.client.File
        self._folder_res = mediafire.client.Folder
        self._downloaderror_exc = mediafire.client.DownloadError
        self._notfound_exc = mediafire.client.ResourceNotFoundError

        self.client = mediafire.client.MediaFireClient()
        self.client.login(app_id=DUPLICITY_APP_ID,
                          email=mediafire_email,
                          password=mediafire_password)

        # //username:password@host/path/to/folder -> path/to/folder
        uri = u'mf:///' + parsed_url.path.split(u'/', 3)[3]

        # Create folder if it does not exist and make sure it is private
        # See MediaFire Account Settings /Security and Privacy / Share Link
        # to set "Inherit from parent folder"
        try:
            folder = self.client.get_resource_by_uri(uri)
            if not isinstance(folder, self._folder_res):
                raise BackendException(u"target_url already exists "
                                       u"and is not a folder")
        except mediafire.client.ResourceNotFoundError:
            # force folder to be private
            folder = self.client.create_folder(uri, recursive=True)
            self.client.update_folder_metadata(uri, privacy=u'private')

        self.folder = folder

    def _put(self, source_path, remote_filename=None):
        u"""Upload file"""
        # Use source file name if remote one is not defined
        if remote_filename is None:
            remote_filename = os.path.basename(source_path.name)

        uri = self._build_uri(remote_filename)

        with self.client.upload_session():
            self.client.upload_file(source_path.open(u'rb'), uri)

    def _get(self, filename, local_path):
        u"""Download file"""
        uri = self._build_uri(filename)
        try:
            self.client.download_file(uri, local_path.open(u'wb'))
        except self._downloaderror_exc as ex:
            raise BackendException(ex)

    def _list(self):
        u"""List files in backup directory"""
        uri = self._build_uri()
        filenames = []
        for item in self.client.get_folder_contents_iter(uri):
            if not isinstance(item, self._file_res):
                continue

            filenames.append(item[u'filename'].encode(u'utf-8'))

        return filenames

    def _delete(self, filename):
        u"""Delete single file"""
        uri = self._build_uri(filename)
        self.client.delete_file(uri)

    def _delete_list(self, filename_list):
        u"""Delete list of files"""
        for filename in filename_list:
            self._delete(filename)

    def _query(self, filename):
        u"""Stat the remote file"""
        uri = self._build_uri(filename)

        try:
            resource = self.client.get_resource_by_uri(uri)
            size = int(resource[u'size'])
        except self._notfound_exc:
            size = -1

        return {u'size': size}

    def _build_uri(self, filename=u''):
        u"""Build relative URI"""
        return (
            u'mf:' + self.folder[u"folderkey"] +
            (u'/' + util.fsdecode(filename))
        )


duplicity.backend.register_backend(u"mf", MediafireBackend)
