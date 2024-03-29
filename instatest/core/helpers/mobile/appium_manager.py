from instatest.core.configuration.instatest_configuration import InstatestConfiguration
from instatest.core.helpers.exceptions import ExternalProcessError
from instatest.core.helpers.process.managed_process import ManagedProcess

''':type : Logger '''


class AppiumManager(ManagedProcess):
    DEFAULT_LOG_FILE = "out/appium_manager.log"

    def __init__(self, appium_path, test_config=None):
        """
        :param str appium_path:
        """
        super(AppiumManager, self).__init__(application_path=appium_path, application_search="appium")
        self._config = test_config  # type: InstatestConfiguration

    def start_appium(self):
        self.log.debug("Starting appium process..")
        super(AppiumManager, self).start_instance_process()
        self.log.debug("Appium process started")

    def get_arguments(self):
        args = []
        if self._config:
            args = ['--log', self._config.appium_log]
        return args

    def wait_for_process(self, queue_size=2, min_wait_s=None, timeout_s=10):
        # Appium will print 2 lines when it is ready
        self.log.debug("Waiting for appium to initialize")
        started = super(AppiumManager, self).wait_for_process(queue_size=queue_size, min_wait_s=min_wait_s, timeout_s=timeout_s)
        self.log.debug("Manager reports appium is initialized: {0}".format(str(started)))

        if not started:
            raise ExternalProcessError(msg="Waited for Appium process but still not detected", process_name=self._name)

    @classmethod
    def get_log_file(cls):
        return cls.DEFAULT_LOG_FILE
