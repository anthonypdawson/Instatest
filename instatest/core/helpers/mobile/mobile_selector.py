# Device/Platform agnostic selector class
from selenium.webdriver.common.by import By

from instatest.core import target_property
from instatest.core.configuration.runtime.global_test_data import TestData
from instatest.core.helpers.abstract_selector import AbstractSelector
from instatest.core.helpers.mobile import mobile_operator
from instatest.core.mobile import devices


class MobileSelector(AbstractSelector):
    def __init__(self,
                 platform: devices.DevicePlatform = None,
                 by: By = None,
                 compare_to: target_property.TargetProperty = None,
                 operator: mobile_operator.MobileOperator = None,
                 value=None):
        super(MobileSelector, self).__init__(by, value)
        self._compare_to = compare_to
        self._platform = platform
        self._operator = operator

    @property
    def compare_to(self) -> target_property.TargetProperty:
        return self._compare_to

    @property
    def operator(self) -> mobile_operator.MobileOperator:
        return self._operator

    @property
    def selector(self):
        raise NotImplementedError()

    @property
    def platform(self):
        if not self._platform:
            context = TestData.get_context()
            if context:
                    self._platform = context.platform
        return self._platform

    def build_predicate(self):
        raise NotImplementedError()

    def for_platform(self, platform):
        return platform == self._platform or self._platform == devices.DevicePlatform.ANY

    def __str__(self):
        return self.to_string()

    def to_string(self):
        platform = "Unknown"
        if '_platform' in self.__dict__:
            platform = self._platform
        return "Platform: {0}, Selector: {1} {2} {3}".format(platform,
                                                             str(self.by), str(self.operator), str(self.value))

    def get_tuple(self):
        return self.by, self.build_predicate()

    def try_get_platform(self):
        try:
            platform = TestData.device.platform
        except:
            platform = None
        return platform
