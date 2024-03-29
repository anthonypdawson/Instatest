import glob
import itertools
from datetime import datetime
from typing import List

import hashlib
import os
from instatest.core.helpers.exceptions import InvalidConfigurationError
from instatest.core.helpers.instatest_object import InstatestObject
from instatest.core.helpers.persistable import Persistable
from instatest.core.mobile.devices import DevicePlatform

platform_extensions = {
    DevicePlatform.IOS: ['app', 'zip', 'ipa'],
    DevicePlatform.ANDROID: ['apk']
}


class MobileApplication(InstatestObject, Persistable):
    JSON_PATH = "./core/configuration/apps/"
    log_name = None
    project = None
    remote_path = None
    instance_url = None
    build_id = None
    bundle_id = None
    app_activity = None
    _platform = None
    _file_size = None

    def __init__(self, *args, **kwargs):
        super().__init__(name="MobileApplication")

        self.name = kwargs.get('app_name', None)
        self._platform: DevicePlatform = kwargs.get('platform', None)
        path = kwargs.get('file_path', None)
        file = kwargs.get('file_name', None)
        self.build_id = kwargs.get("build_id", None)
        self.bundle_id = kwargs.get("bundle_id", None)
        self.project = kwargs.get("project", None)
        self.remote_path = kwargs.get("remote_path", None)
        self.instance_url = kwargs.get("instance_url", None)
        self.app_activity = kwargs.get("app_activity", None)

        self._md5 = kwargs.get("md5", None)

        if path:
            if '~' in path:
                path = os.path.expanduser(path)
            if '$' in path:
                path = os.path.expandvars(path)
            if os.path.exists(path):
                path = os.path.abspath(path)

        self._application_path = path
        self._application_file = file
        self._full_path = None
        self._unique_id = kwargs.get("unique_id", None)
        self._file_size = kwargs.get("file_size", None)
        self._file_modified = kwargs.get("file_modified", None)

    def get_default_extensions(self, platform):
        return platform_extensions.get(platform, [])

    @classmethod
    def from_application_file(cls, path_to_file, **kwargs):
        platform = None
        app_name = None
        ''' Try to figure out platform based on extension '''

        if len(path_to_file) < 4:
            raise InvalidConfigurationError("Path to application file is too short. Path: {0}".format(path_to_file))
        extension = path_to_file[-3:]  # type: str
        if extension.upper() == "ZIP":
            platform = DevicePlatform.IOS
        elif extension.upper() == "APK":
            platform = DevicePlatform.ANDROID
        else:
            raise InvalidConfigurationError(
                "Couldn't figure out platform from extension. Found {0} but expecting zip or apk".format(extension))
        app_name = os.path.basename(path_to_file)[:-4]
        app_dir = os.path.abspath(os.path.dirname(path_to_file))
        app_obj = MobileApplication(app_name=app_name, platform=platform, path=app_dir,
                                    file=os.path.basename(path_to_file))
        if 'applicant' in path_to_file:
            app_obj.project = 'applicant'
            if app_obj.platform:
                app_obj.name = "{0}_{1}".format(app_obj.project, app_obj.platform.value)
                if 'unique_id' in kwargs:
                    app_obj.name += "_{0}".format(kwargs['unique_id'])
        elif 'business' in path_to_file:
            app_obj.project = 'business'

        if 'name' in kwargs:
            app_obj.name = kwargs['name']
        if 'build_id' in kwargs:
            app_obj.build_id = kwargs['build_id']
        if 'bundle_id' in kwargs:
            app_obj.bundle_id = kwargs['bundle_id']
        if 'project' in kwargs:
            app_obj.project = kwargs['project']
        app_obj.save()
        return app_obj

    @property
    def platform(self):
        p = self._platform
        if isinstance(p, str):
            p = DevicePlatform.from_name(p)
        return p

    @property
    def file_size(self):
        if hasattr(self, "_file_size"):
            return self._file_size
        return None

    def calculate_file_size(self):
        self._file_size = os.path.getsize(self.file_path)
        return self._file_size

    def get_file_modified(self):
        self._file_modified = os.path.getmtime(self.file_path)
        return self._file_modified

    def file_modified(self):
        old_time = self._file_modified
        new_time = self.get_file_modified()
        return old_time == new_time

    def file_size_changed(self):
        old_size = self._file_size
        new_size = self.calculate_file_size()
        return old_size == new_size

    def update_md5(self):
        needs_hash = True
        if '_md5' in self.__dict__ and self._md5 is not None:
            needs_hash = self.file_size_changed() is False and self.file_modified() is False
        return needs_hash

    @property
    def json_file(self):
        file_path = "{0}_{1}".format(self.name, self.platform.value)
        if self.build_id:
            file_path = "{0}_{1}".format(file_path, self.build_id)
        return os.path.join(self.JSON_PATH, "{0}.json".format(file_path))

    def save(self, **kwargs):
        from instatest.core.configuration.instatest_configuration import InstatestConfiguration
        c = InstatestConfiguration()
        c.add_application(self)

    @staticmethod
    def calculate_md5(path):
        hash_md5 = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def get_unique_id(self):
        if '_unique_id' not in self.__dict__ or self._unique_id is None:
            self._unique_id = datetime.utcnow().timestamp()

        return self._unique_id

    def get_unique_file_name(self):
        return "{0}_{1}".format(self.get_unique_id(), self.file_name)

    def is_platform(self, device_platform):
        return self.platform == device_platform.value or self.platform == device_platform

    @property
    def file_path(self):
        if '_full_path' not in self.__dict__ or self._full_path is None or self._full_path == "":
            if self.remote_path and ':' in self.remote_path:
                self._full_path = self.remote_path
            else:
                if '$HOME' or '~' in self._application_path:
                    self._application_path = os.path.expanduser(self._application_path)
                if not self._application_file:
                    self._application_file = self._determine_application_file()
                self._full_path = os.path.join(self._application_path, self._application_file)
        return self._full_path

    @file_path.setter
    def file_path(self, full_path):
        fdir = os.pathsep.split(full_path)[:-1]
        fname = os.pathsep.split(full_path)[-1]

        self._application_path = fdir
        self._application_file = fname

    @property
    def file_dir(self):
        return self._application_path

    @property
    def file_name(self):
        return self._application_file

    def is_zip_file(self):
        return self.file_name.endswith(".zip")

    def multiple_file_types(self, patterns):
        all = []
        for f in itertools.chain.from_iterable(glob.iglob(pattern) for pattern in patterns):
            all.append(f)
        return all

    def _determine_application_file(self):
        # Look for any appropriate files
        matching_files = self._get_app_files_from_path(self._application_path)
        chosen_app = None
        file_count = len(matching_files)

        if file_count == 1:
            chosen_app = matching_files[0]
        elif file_count > 1:
            self.log.warning(
                "Application does not have a file name defined.  Found {0} files that may be applications "
                "in path: {1}. Will attempt to attempt to find apps in the order: release > debug ".format(
                    str(file_count), self._application_path))
            chosen_app = self._prioritize_app_for_environments(matching_files)
        else:
            raise InvalidConfigurationError("No applications found in path {0}".format(self._application_file))
            # There is a single file with the correct extension. Use this by default

        return os.path.basename(chosen_app)

    def _get_app_files_from_path(self, path) -> List:
        default_extensions = self.get_default_extensions(self.platform)

        file_pattern = [os.path.join(path, "*.{0}".format(e)) for e in default_extensions]
        self.log.debug("Attempting to find application file. Pattern: {0}".format(file_pattern))
        files = self.multiple_file_types(file_pattern)
        return files

    def _prioritize_app_for_environments(self, file_list):
        environments = ['release', 'debug']
        for environment in environments:
            file = next((f for f in file_list if environment.lower() in f.lower()), None)
            if file:
                self.log.debug("Found application for environment {0}.  File: {1}".format(environment, file))
                return file
        raise InvalidConfigurationError(
            "Multiple files found in application path.  Could not determine environment types.  Will not choose randomly from list. \n{0}".format(
                '\n'.join(file_list)))

    @classmethod
    def load(cls, obj_data: dict):
        app_name = obj_data.get("name", None)
        platform_name = obj_data.get("platform", None)
        obj_data['platform'] = DevicePlatform.from_name(platform_name)
        app = cls(app_name=app_name, **obj_data)
        return app

    def export(self):
        app_data = {
            "file_name": self._application_file,
            "file_path": self._application_path,
            "bundle_id": self.bundle_id,
            "app_activity": self.app_activity,
            "build_id": self.build_id,
            "instance_url": self.instance_url,
            "name": self.name,
            "platform": self._platform.value if isinstance(self._platform, DevicePlatform) else self._platform,
            "remote_path": self.remote_path,
            "unique_id": self._unique_id,
            "file_size": self.file_size,
            "project": self.project
        }
        app_data = {k: v for k, v in app_data.items() if v}
        return app_data
