from appium.webdriver.common.mobileby import MobileBy
from selenium.webdriver.common.by import By

from instatest.core.helpers.exceptions import InvalidSelectorException
from instatest.core.helpers.mobile import MobileOperator
from instatest.core.helpers.mobile.mobile_selector import MobileSelector
from instatest.core.mobile.devices import DevicePlatform
from instatest.core.target_property import TargetProperty


class AndroidSelector(MobileSelector):
    SUPPORTED_PROPERTIES = (
        TargetProperty.Text, TargetProperty.ResourceId, TargetProperty.Description, TargetProperty.AccessibilityId,
        TargetProperty.ContentDescription, TargetProperty.XPath, TargetProperty.Class)
    PROPERTY_OPERATORS = {
        TargetProperty.Class: [MobileOperator.Equals, MobileOperator.Matches],
        TargetProperty.ContentDescription: [MobileOperator.Equals, MobileOperator.Contains, MobileOperator.StartsWith,
                                            MobileOperator.Matches],
        TargetProperty.ResourceId: [MobileOperator.Equals, MobileOperator.Matches],
        TargetProperty.Text: [MobileOperator.Equals, MobileOperator.Contains, MobileOperator.StartsWith,
                              MobileOperator.Matches],
        TargetProperty.XPath: []  # If using XPath - should not get to this check!  If so, something bad happened!
    }
    SUPPORTED_OPERATORS = (
        MobileOperator.Contains,
        MobileOperator.EndsWith,  # This isn't directly supported by UiSelector - we use Matches with a regex
        MobileOperator.StartsWith,
        MobileOperator.Equals,
        MobileOperator.Matches
    )

    @classmethod
    def ByXPath(cls, xpath):
        a = AndroidSelector(MobileBy.XPATH, TargetProperty.XPath, MobileOperator.Equals, xpath)
        return a

    @classmethod
    def ById(cls, val):
        return AndroidSelector(MobileBy.ANDROID_UIAUTOMATOR, TargetProperty.ContentDescription, MobileOperator.Equals,
                               val)

    @classmethod
    def ByResourceId(cls, val):
        return AndroidSelector(MobileBy.ANDROID_UIAUTOMATOR, TargetProperty.ResourceId, MobileOperator.Equals, val)

    def __init__(self, by, compare_to, operator, value):
        super(AndroidSelector, self).__init__(DevicePlatform.ANDROID, by, compare_to, operator, value)

    @property
    def by(self) -> By:
        if self._by is None:
            return MobileBy.ANDROID_UIAUTOMATOR
        return self._by

    '''
    Builds the UIAutomator lookup based on the property being matched and how it's matched
    Only Text, ResourceId, AccessibilityId and Description are supported by UiSelector
    They're built by appending their text values with the operator value 
    ex: MobileSelectBy.ResourceId is resourceId
        MobileOperator.StartsWith appends 'StartsWith({0})'
        Format the string with the value of the look up and you end up with
        
        new UiSelector().resourceIdStartsWith(\"someValue\")
        
    '''

    def build_predicate(self):
        if self.by == MobileBy.XPATH or self.by == MobileBy.ID or self.compare_to is None or self.operator is None:
            return self.value
        target_property = self.compare_to

        valid_selector = self._validate_selector(target_property, self.operator)

        if not valid_selector:
            self.log.warning(
                "Selector combinations did not pass validation but exception wasn't raised. Platform: Android, Property: {0}, Operator: {1}".format(
                    target_property, self.operator))
        if target_property in [TargetProperty.AccessibilityLabel, TargetProperty.AccessibilityId]:
            target_property = TargetProperty.ContentDescription  # For android use content description for looking up test/accessiblity id

        if target_property == TargetProperty.Description:
            target_property = TargetProperty.ContentDescription  # Description is an alias for content description

        selector_method = self._get_selector_method().format(self.value)
        selector = 'new UiSelector().{0}{1}'.format(target_property, selector_method)

        return selector

    def get_tuple(self):
        if self.by == MobileBy.ACCESSIBILITY_ID or self.by == MobileBy.ID:
            return MobileBy.ID, self.value
        return self.by, self.build_predicate()

    @property
    def selector(self):
        return self.build_predicate()

    def _validate_selector(self, target_property, operator, hide_exception=False):
        if target_property not in self.SUPPORTED_PROPERTIES:
            self.log.warning("Currently {0} is not supported".format(target_property))
            if not hide_exception:
                raise InvalidSelectorException(msg="Invalid target property for android selector",
                                               platform=DevicePlatform.ANDROID, property=target_property)
            return False

        if operator not in self.SUPPORTED_OPERATORS:
            self.log.warning("Currently operator {0} is not supported".format(operator))
            if not hide_exception:
                raise InvalidSelectorException(msg="Invalid operator for Android Selector",
                                               platform=DevicePlatform.ANDROID,
                                               operator=operator)
            return False

        supported_operators = self.PROPERTY_OPERATORS.get(target_property, None)
        if supported_operators:
            if operator not in supported_operators:
                self.log.warning("Operator {0} not supported for property {1}".format(operator, target_property))
                if not hide_exception:
                    raise InvalidSelectorException(msg="Invalid combination for Android Selector",
                                                   platform=DevicePlatform.ANDROID, target=target_property,
                                                   operator=operator)
                return False

        return True

    def _get_selector_method(self):
        sel_method = ""
        if self.operator == MobileOperator.Contains:
            sel_method = "Contains(\"{0}\")"  # ex: "textContains('text')
        elif self.operator == MobileOperator.StartsWith:
            sel_method = "StartsWith(\"{0}\")"  # ex: "textStartsWith('text')
        elif self.operator in [MobileOperator.EndsWith, MobileOperator.Matches]:
            regex_match = "Matches(\"{0}\")"
            if self.operator == MobileOperator.EndsWith:
                self.operator = MobileOperator.Matches  # Switch to regex search
                regex_match = "Matches(\".*{0}$\")"
            sel_method = regex_match  # ex: "textMatches('.*text$')
        elif self.operator == MobileOperator.Equals:
            sel_method = "(\"{0}\")"  # Ex: "text('text')

        return sel_method
