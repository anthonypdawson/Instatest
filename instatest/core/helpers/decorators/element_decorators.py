from typing import Any, Callable, Dict, List, Optional

from appium.webdriver import WebElement
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException

import instatest.core.driver.mobile_driver_context as mobile_driver_context
from instatest.core.helpers.mobile.mobile_selector import MobileSelector
from instatest.core.helpers.selectors.selectors import AndroidAutomatorSelector, Selector
from instatest.core.helpers.test_logger import get_logger
from instatest.core.mobile.devices import DevicePlatform

log = get_logger('ElementDecorator')


def get_cache(obj) -> Dict:
    if not hasattr(obj, 'selector_cache'):
        obj.__dict__['selector_cache'] = {}
    return getattr(obj, "selector_cache")


def lookup_elements(context: mobile_driver_context.MobileDriverContext,
                    selector: MobileSelector):
    return context.find_elements_by(selector)


def element_stale(obj, element: WebElement):
    is_stale = False
    try:
        element.is_displayed()
    except StaleElementReferenceException as stale_ex:
        is_stale = True
        obj.log.warning("cached element is stale")
    except WebDriverException as wde:
        obj.log.warning("Error checking for staleness of element.  {0}".format(
            wde.msg))
    except Exception as e:
        obj.log.warning("Unknown exception checking staleness of element")
        raise e
    return is_stale


def element_in_cache(obj, cache, func_name):
    if func_name in cache:
        cached_element = cache[func_name]
        if cached_element:
            if isinstance(cached_element, WebElement):
                return not element_stale(obj, cached_element)
    return False

class element:
    selector_choices = [
        'id', 'partial_id', 'text', 'partial_text', 'resource_id'
                                                    'xpath', 'android_selector'
    ]

    def __init__(self, selector=None, *args, **kwargs):
        """
            Decorator that will attempt to find and return the webelement found with a given selector
            Ex:
            class FooScreen:
                @element(id='email_input')
                def email_input(self):
                  pass

            f = FooScreen()
            f.email_input.set_text("my_email@gmail.com")

        :param MobileSelector selector:  Selector to use when looking up this element
        :param kwargs: Adds easier methods for specifying selectors as well as mapping platform specific selectors

                       Keys mapped to types of selectors: id, partial_id, text, partial_text, xpath {ex: partial_text='Input'}
                       or pass the name of the platform you're specifying {ex: android=IdSelector('foo')}
        """
        self.context = None
        self.selector_map = {}
        if kwargs and len(kwargs) > 0:
            if selector is None:
                selector = self._parse_selector_argument(kwargs)
            self.context = kwargs.pop('dc', None)
            for platform_name, s in kwargs.items():
                platform = DevicePlatform.from_name(platform_name)
                if platform:
                    self.selector_map[platform] = s
        self.selector = selector

    def _parse_selector_argument(self, selector_args):
        # Return first match
        for choice in self.selector_choices:
            if choice in selector_args:
                return self._create_selector(choice, selector_args[choice])
        return None

    def _create_selector(self, key, val):
        if key == 'id':
            return Selector.by_id(val)
        elif key == 'partial_id':
            return Selector.by_partial_content_description(val)
        elif key == 'text':
            return Selector.by_text(val)
        elif key == 'partial_text':
            return Selector.by_partial_text(val)
        elif key == 'xpath':
            return Selector.by_xpath(val)
        elif key == 'resource_id':
            return Selector.by_resource_id(val)
        elif key == 'android_selector':
            return AndroidAutomatorSelector(val)
        return None

    def __call__(self, selector=None, *args, **kwargs):
        return element(self.selector, args, kwargs)

    def __get__(self, obj, obj_cls, *args, **kwargs) -> WebElement:
        context = None
        if self.context:
            context = self.context
        else:
            context = getattr(
                obj, 'driver_context',
                None)  # type: mobile_driver_context.MobileDriverContext
        if context is None:
            raise AttributeError(
                "Object {0} does not have driver context".format(obj_cls))
        selector = self._get_selector(context)
        if selector is None:
            raise AttributeError(
                "Could not find appropriate selector for this property")

        return self._get_element(context, selector)

    def _get_selector(self,
                      context: mobile_driver_context.MobileDriverContext):
        element_selector = None
        if self.selector_map and len(self.selector_map) > 0:
            platform = context.device.platform
            element_selector = self.selector_map.get(platform, None)
        if element_selector is None:
            element_selector = self.selector
        return element_selector

    def _get_element(self, context: mobile_driver_context.MobileDriverContext,
                     selector) -> Optional[WebElement]:
        el: WebElement = None
        try:
            # If parent is webelement we need to call find_element with a tuple
            if isinstance(context, WebElement):
                by, val = selector.get_tuple()
                el = context.find_element(by, val)
            else:
                el = context.find_element_by(selector)
        except WebDriverException as wde:
            log.warning("WebDriverException looking up element. {0}".format(wde))

        log.debug("Element found: {0}".format(str(el is not None)))
        return el

    def getter(self, selector, *args, **kwargs):
        return type(self)(selector, args, kwargs)

    @classmethod
    def by_id(cls, element_id: str):
        return cls(id=element_id)

    @classmethod
    def by_text(cls, element_text: str):
        return cls(text=element_text)

    @classmethod
    def by_partial_id(cls, partial_id: str):
        return cls(partial_id=partial_id)

    @classmethod
    def by_partial_text(cls, partial_text: str):
        return cls(partial_text=partial_text)

    @classmethod
    def by_resource_id(cls, resource_id: str):
        return cls(resource_id=resource_id)

    @classmethod
    def by_xpath(cls, xpath: str):
        return cls(xpath=xpath)


class elements(element):
    def __init__(self, selector=None, *args, **kwargs):
        """
            Decorator that will attempt to find and return the webelement(s) found with a given selector
            Ex:
            class FooScreen:
                @elements(partial_id='_jobs')
                def jobs(self):
                  pass

            f = FooScreen()
            all_jobs = f.jobs
            visible_jobs = [j for j in all_jobs if j.is_visible()]

        :param MobileSelector selector:  Selector to use when looking up this element
        :param kwargs: Adds easier methods for specifying selectors as well as mapping platform specific selectors

                       Keys mapped to types of selectors: id, partial_id, text, partial_text, xpath {ex: partial_text='Input'}
                       or pass the name of the platform you're specifying {ex: android=IdSelector('foo')}
        """
        self.selector_map = {}
        if kwargs and len(kwargs) > 0:
            if selector is None:
                selector = self._parse_selector_argument(kwargs)
            for platform_name, s in kwargs.items():
                platform = DevicePlatform.from_name(platform_name)
                if platform:
                    self.selector_map[platform] = s
        self.selector = selector

    def __call__(self, selector=None, *args, **kwargs):
        return elements(self.selector, args, kwargs)

    def __get__(self, obj, obj_cls, *args, **kwargs) -> List[WebElement]:
        context = getattr(
            obj, 'driver_context',
            None)  # type: mobile_driver_context.MobileDriverContext
        if context is None:
            raise AttributeError(
                "Object {0} does not have driver context".format(obj_cls))
        selector = self._get_selector(context)
        if selector is None:
            raise AttributeError(
                "Could not find appropriate selector for this property")

        return self._get_elements(context, selector)

    def _get_elements(self, context: mobile_driver_context.MobileDriverContext,
                      selector) -> Optional[List[WebElement]]:
        elements = None
        try:
            by, val = selector.get_tuple()
            elements = context.find_elements(by, val)
        except WebDriverException as wde:
            log.warning("WebDriverException looking up elements. {0}".format(wde))

        return elements
