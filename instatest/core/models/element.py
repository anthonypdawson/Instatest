from appium.webdriver import WebElement, webdriver
from appium.webdriver.webdriver import WebDriver
from instatest.core.configuration.runtime.global_test_data import TestData
from instatest.core.helpers.abstract_selector import AbstractSelector
from instatest.core.helpers.instatest_object import InstatestObject
from instatest.core.helpers.test_logger import get_logger
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from instatest.core.driver import IWebDriverContext


class AbstractElement(InstatestObject):
    def _get_web_element(self) -> WebElement:
        raise NotImplementedError()

    def get_web_element(self) -> WebElement:
        return self._get_web_element()


class Element(AbstractElement):
    log = get_logger("Element")

    def __init__(self, selector: AbstractSelector, driver_context, parent: AbstractElement = None, index=None,
                 wait=None):
        self._selector = selector
        self._parent = parent
        self._index = index
        self._wait = wait
        self._context = driver_context

    @property
    def selector(self):
        return self._selector

    def _get_context(self) -> IWebDriverContext:
        if not self._context:
            self._context = TestData.get_driver_context()
        return self._context

    def _get_driver(self) -> WebDriver:
        return self._get_context().get_webdriver()

    def _get_web_element(self) -> WebElement:
        base: webdriver.WebDriver = self._get_driver()
        if self._parent:
            base: WebElement = self._parent.get_web_element()
        element = base.find_element(self._selector.by, self._selector.value)
        return element

    def _wait_for_element(self, timeout=None) -> WebElement:
        element = None
        if timeout is None:
            timeout = TestData.get_default_timeout()
        base: webdriver.WebDriver = self._get_driver()
        if self._parent:
            base: WebElement = self._parent
        try:
            element = WebDriverWait(base, timeout, poll_frequency=TestData.get_polling_seconds(),
                                    ignored_exceptions=[NoSuchElementException, TimeoutException]).until(
                expected_conditions.presence_of_element_located((self.selector.by, self.selector.value)))
        except BaseException as e:
            self.log.warning("Exception waiting for element. Error: {0} {1}".format(e, e.args))
        return element
