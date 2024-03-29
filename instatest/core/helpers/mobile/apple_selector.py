from appium.webdriver.common.mobileby import MobileBy
from instatest.core.helpers.mobile import MobileOperator
from instatest.core.helpers.mobile.mobile_selector import MobileSelector
from instatest.core.mobile.devices import DevicePlatform
from instatest.core.target_property import TargetProperty
from selenium.webdriver.common.by import By


class AppleSelector(MobileSelector):
    SUPPORTED_PROPERTIES = (
        TargetProperty.Name,
        TargetProperty.TestID,
        TargetProperty.AccessibilityId
    )
    SUPPORTED_OPERATORS = (
        MobileOperator.Contains,
        MobileOperator.Equals
    )

    def __init__(self, by, compare_to, operator, value):
        if by is None:
            by = MobileBy.IOS_PREDICATE
        super(AppleSelector, self).__init__(DevicePlatform.IOS, by, compare_to, operator, value)

    @property
    def by(self) -> By:
        if self._by is None:
            return MobileBy.IOS_PREDICATE
        else:
            return self._by

    def build_predicate(self):
        self.log.debug("MobileBy: {0}".format(self.by))
        if self.by != MobileBy.IOS_PREDICATE:
            self.log.warning("Currently only supports IOS Predicate selectors")
            raise NotImplementedError()
        selector = ""
        if self.compare_to not in self.SUPPORTED_PROPERTIES:
            self.log.warning("Currently does not support property: {0}".format(self.compare_to))
            raise NotImplementedError()

        if self.compare_to == TargetProperty.Name:
            selector += "name "

        if self.operator not in self.SUPPORTED_OPERATORS:
            self.log.warning("Currently does not support operator: {0}".format(self.operator))
            raise NotImplementedError()

        selector += self.get_operator_string()
        selector += " '{0}'".format(self.value)

        return selector

    def get_operator_string(self):
        if self.operator == MobileOperator.Contains:
            return "CONTAINS"
        if self.operator == MobileOperator.Equals:
            return "=="
        return None

