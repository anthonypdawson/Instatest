from typing import TypeVar, Dict

import os

from instatest.core.extensions.str import is_empty
from instatest.core.helpers.instatest_object import InstatestObject
from enum import Enum

from instatest.core.helpers.persistable import Persistable

"""
Example for connecting to appium to run a test on an apple device

>>> d = webdriver.Remote(desired_capabilities={'platformName': "ios", "platformVersion": "10.3", 'appName': 'Instawork', "deviceName": "iPhone 6s", "app": "path/to/app", "automationName": "XCUITest" },command_executor="http://localhost:4723/wd/hub");

"""


class DevicePlatform(Enum):
    ANDROID = "android"
    IOS = "ios"
    ANY = "any"

    @classmethod
    def from_name(cls, platform_name):
        platform_name = platform_name.lower()
        if platform_name in ['ios', 'iphone', 'apple']:
            return DevicePlatform.IOS
        if platform_name in ['android']:
            return DevicePlatform.ANDROID
        return None


T = TypeVar('T')


class Device(InstatestObject, Persistable):
    JSON_PATH = "~/.instatest/"

    def __init__(self: T, name=None, version=None, platform: DevicePlatform = None, *args, **kwargs) -> T:
        self._bundle_id = None
        super(Device, self).__init__('Device' if name is None else name)
        self._emulated = kwargs.get('emulated', True)
        self._name = name
        self._version = version
        self._platform = platform
        self._data = kwargs


    def get_json_file(self):
        return os.path.join(self.JSON_PATH, "{0}_{1}_{2}.json".format(self.name, self.version, self.platform))

    @classmethod
    def from_sauce_platform(cls, sauce_platform: dict):
        platform = None
        platform_name = sauce_platform['api_name']
        if platform_name == "android":
            platform = DevicePlatform.ANDROID
        elif platform_name == "iphone":
            platform = DevicePlatform.IOS
        d = Device(name=sauce_platform['device'], version=sauce_platform['short_version'], platform=platform)

        return d

    @classmethod
    def from_sauce_platforms(cls, sauce_platforms):
        devices = []
        for s in sauce_platforms:
            d = Device.from_sauce_platform(s)
            devices.append(d)
        return devices

    @property
    def emulated(self):
        return self._emulated

    # Bundle id might be used instead of app when connecting to the driver
    @property
    def bundle_id(self):
        if hasattr(self, '_bundle_id'):
            return self._bundle_id
        return None

    @bundle_id.setter
    def bundle_id(self, bundle_id):
        self._bundle_id = bundle_id

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def platform(self) -> DevicePlatform:
        p = self._platform
        if isinstance(p, str):
            p = DevicePlatform.from_name(p)
        return p

    @property
    def version(self) -> str:
        return self._version

    @version.setter
    def version(self, version):
        self._version = version

    @property
    def device_name(self):
        raise NotImplementedError()

    def get_desired_capabilities(self):
        raise NotImplementedError()

    def __str__(self):
        return self.name

    @classmethod
    def load(cls, obj_data):
        platform_name = obj_data.get('platform', None)
        if platform_name:
            platform = DevicePlatform.from_name(platform_name)
            if platform == DevicePlatform.ANDROID:
                return AndroidDevice.load(obj_data)
            elif platform == DevicePlatform.IOS:
                return AppleDevice.load(obj_data)
        return cls(kwargs=obj_data)

    def export(self) -> Dict:
        app_data = {
            "app": None,
            "bundle_id": self.bundle_id,
            "name": self.name,
            "platform": self.platform.value,
            "version": self.version
        }
        return app_data


class AndroidDevice(Device):
    def __init__(self, name=None, version=None, avd=None, device_name=None, *args, **kwargs):
        super(AndroidDevice, self).__init__(name, version, DevicePlatform.ANDROID, args, kwargs)
        self._device_name = device_name
        self._name = name
        self._version = version
        self._avd = avd

    @property
    def avd(self) -> str:
        return self._avd

    @property
    def emulated(self) -> bool:
        default_val = super().emulated
        if not default_val or default_val is False:
            default_val = is_empty(self=self.avd) is False or 'emulator' in self.device_name.lower()
        return default_val


    @property
    def device_name(self) -> str:
        return self._device_name

    def __str__(self):
        return self.device_name

    def export(self):
        app_data = super().export()
        app_data["avd"] = self._avd
        return app_data

    @classmethod
    def load(cls, obj_data: Dict):
        name = obj_data.get("name", None)
        version = obj_data.get("version", None)
        avd = obj_data.get("avd", None)
        device_name = obj_data.get("device_name", None)
        other_fields = {k:v for k,v in obj_data.items() if k not in ['name', 'version', 'avd', 'device_name']}
        d = cls(name=name, version=version, avd=avd, device_name=device_name, kwargs=other_fields)
        return d


class AppleDevice(Device):
    def __init__(self, name=None, version=None, *args, **kwargs):
        super(AppleDevice, self).__init__(name, version,DevicePlatform.IOS)
        self._device_name = kwargs.get('device_name', None)

    @property
    def device_name(self):
        return self._device_name

    def __str__(self):
        return self.device_name

    def export(self):
        obj_data = super().export()
        obj_data['device_name'] = self.device_name

        return obj_data

    @classmethod
    def from_dict(cls, obj_data):
        name = obj_data.getf("name", None)
        device_name = obj_data.get("device_name", None)
        version = obj_data.get("version", None)
        other_fields = {k:v for k,v in obj_data.items() if k not in ['name', 'device_name', 'version']}
        return cls(name=name, device_name=device_name, version=version, kwargs=other_fields)
