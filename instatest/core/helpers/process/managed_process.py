import os
import subprocess
import sys
import time
from multiprocessing import Process
from queue import Empty, Queue
from typing import List, Optional

import psutil

from instatest.core.helpers.instatest_object import InstatestObject
from instatest.core.helpers.test_logger import get_logger

ON_POSIX = 'posix' in sys.builtin_module_names


class ManagedProcess(InstatestObject):
    processes = []  # type: List[Process]
    queue = None


    def __init__(self, application_path=None, cmd_list=None, application_search=None, *args, **kwargs):
        self._path = application_path
        self._cmd_list = cmd_list
        self._process: subprocess.Popen = None
        self._queue = None  # type: Queue
        self._threads = None  # type: List[Process]
        self._application_search = application_search
        self._arguments = kwargs.get("arguments", [])
        self._cwd = kwargs.get("cwd", None)
        self._name = kwargs.get("name", None)
        self._search_for_existing = False
        super().__init__(name=self.name)


    @property
    def pid(self):
        if self._process:
            return self._process.pid
        return None


    def start_instance_process(self, wait_for_process: bool = None):
        if self._search_for_existing:
            if self.search_for_process():
                return True
        command_line = []

        if self._cmd_list:
            self.log.debug("cmd_list: {}".format(self._cmd_list))
            command_line = self._cmd_list
        else:
            self.log.debug("Path: {}".format(self._path))
            if self._path:
                command_line: list = self._path.split(" ")
        if self.has_arguments():
            command_line.extend(self.get_arguments())

        self.log.debug(command_line)
        if not self._cwd:
            self._cwd = os.path.abspath(".")  # Use current directory if none defined

        self._process = subprocess.Popen(
            command_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=ON_POSIX, cwd=self._cwd)

        self.log.debug("Started process {0}, pid: {1}".format(self._name, self._process.pid))

        self._queue = Queue()

        proc_logger = get_logger(
            "Managed_Process", file=os.path.abspath("./out/" + str(self.name.replace(" ", "_") + ".log")))
        thread_args = (self._process.stdout, self._process.stderr, self._queue, proc_logger)
        self._threads = [Process(target=enqueue_output, args=thread_args)]
        for t in self._threads:
            t.daemon = True
            t.start()
        if wait_for_process and wait_for_process is True:
            self.wait_for_process()


    @property
    def name(self):
        name = self._name
        if name is None:
            name = self.__class__.__name__
        return name


    def has_arguments(self):
        return isinstance(self._arguments, list) and len(self._arguments) > 0


    def get_threads(self) -> List[Process]:
        return self._threads


    def get_process(self):
        return self._process


    def get_arguments(self) -> List[str]:
        return self._arguments


    def kill_processes(self):
        processes_stopped = True
        try:
            return_code = 0
            if self._threads is None or len(self._threads) == 0:
                process = self.search_for_process()
                if process is not None:
                    process.kill()
                    if process.is_running():
                        self._threads = [process]

            if self._threads:
                self.log.debug("Found threads, killing {}".format(len(self._threads)))
                self.log.debug("Killing processes: " + str(len(self._threads)))
                for t in self._threads:
                    if t and psutil.pid_exists(t.pid):
                        proc = psutil.Process(pid=t.pid)
                        self.log.debug("Thread is found: Checking children and terminating")
                        processes_stopped = self.kill_with_children(process=proc)
                    if not psutil.pid_exists(t.pid):
                        self._threads.remove(t)

            found_procs = self.search_for_processes()
            self.log.debug("Found process count: {}".format(len(found_procs)))
            for found in found_procs:
                processes_stopped = processes_stopped and self.terminate_process(found)
                self.log.debug("Terminated found proc {0}".format(found.is_running() is False))
        except Exception as e:
            self.log.error("Exception caught killing process. ", e)
        return processes_stopped


    def terminate_process(self, process: psutil.Process = None):
        if process:
            try:
                if process.is_running():
                    process.terminate()
                    process.wait(timeout=5)
                    return process.is_running() is False
            except Exception as e:
                self.log.warning("Exception terminating process. {}".format(e))
        return True

    def get_return_code(self, timeout_s=5):
        return_code = None
        if self._process:
            return_code = self._process.poll()
        return return_code


    def kill_process(self, process: psutil.Process = None):
        if process:
            try:
                if process.is_running():
                    process.kill()
                    process.wait(timeout=5)
                    return process.is_running() is False
            except Exception as e:
                self.log.warning("Exception killing process. {}".format(e))
        return False


    def kill_with_children(self, process_id=None, process: Process = None) -> bool:
        children_killed: bool = True

        try:
            if process:
                if not isinstance(process, Process):
                    process_id = process.pid
                if process_id is None:
                    self.log.warning("Trying to kill process but can't find pid or method called without passing process or ID")
                    return False
                else:
                    process = psutil.Process(pid=process_id)

            children = process.children(recursive=True)
            if len(children) > 0:
                self.log.debug("Found {0} children".format(str(len(children))))
                for c in children:
                    self.log.debug("Killing process pid {0}".format(str(c.pid)))
                    self.kill_process(c)
                    children_killed = children_killed and c.is_running() is False
            self.kill_process(process)
            return_code = process.wait(timeout=5)
            children_killed = children_killed and (process.is_running() is False)
        except ChildProcessError as cpe:
            self.log.warning("Child Process Error attempting to kill process: {0}. Error: {1}".format(str(process.pid), cpe))
        except TimeoutError as te:
            self.log.error(
                "Timeout error encountered waiting for process to exit.  Process: {0}, Error: {1}".format(process, te))
        except Exception as e:
            self.log.warning("Exception in p.terminate")
            self.log.warning(e)
        return children_killed


    def wait_for_process(self, queue_size=None, min_wait_s=None, timeout_s=20):
        start_time = time.time()
        elapsed_time = 0
        # wait until we start getting output from the process
        break_loop = False
        process_started = False
        self.log.debug("Waiting for process to start.  Checking queue size: " + str(queue_size) + ", Min_wait: " +
                       str(min_wait_s))
        while not break_loop:
            elapsed_time = time.time() - start_time
            if not process_started:
                queue_size_met = self._queue.qsize() >= queue_size if queue_size else self._queue.qsize() > 0
                if queue_size_met:
                    self.log.debug("Process started - queue size: " + str(self._queue.qsize()))
                    if not min_wait_s:
                        return True
                    process_started = break_loop = True

            if not process_started and elapsed_time >= timeout_s:
                break_loop = True

            if break_loop and min_wait_s and elapsed_time < min_wait_s:
                break_loop = False
            time.sleep(0.5)
        # print("Started: " + str(process_started))
        return process_started


    def read_stdout(self):
        line = ""
        while line:
            try:
                line = self._queue.get_nowait()
            except Empty:
                line = None
                self.log.debug("no output in process queue")
            else:
                self.log.debug(line)


    def search_for_process(self):
        for p in psutil.process_iter():
            try:
                if p.name() == self._application_search or self._application_search in p.name(
                ) or self._application_search in p.cmdline() or self._application_search in p.cmdline():
                    return p
            except psutil.AccessDenied:
                # Don't report error, this just means we don't have access to inspect the process
                pass
            except ProcessLookupError:
                # Don't report error, this just means we don't have access to inspect the process
                pass
            except Exception as e:
                self.log.warning("Caught exception iterating processes {}".format(e))
        return None


    def search_for_processes(self) -> List[psutil.Process]:
        processes: list = []
        for p in psutil.process_iter():
            try:
                if self._application_search in p.cmdline():
                    processes.append(p)
            except psutil.AccessDenied:
                # Don't report error, this just means we don't have access to inspect the process
                pass
            except ProcessLookupError:
                # Don't report error, this just means we don't have access to inspect the process
                pass
            except Exception as e:
                self.log.warning("Caught exception iterating processes {}".format(e))
        return processes


    def is_running(self) -> bool:
        self.log.debug("Checking if process is running. Searching for {0}".format(self._application_search))
        process = self.search_for_process()
        running = process is not None
        if not running:
            threads = self.get_threads()
            if threads and len(threads) > 10:
                self.log.debug("Threads have been created")
                for t in threads:
                    if t.is_alive():
                        self.log.debug("Process is alive")
                        running = True
        self.log.debug("Returning {} for is_running".format(str(running)))
        return running

    def wait_for_exit(self, timeout_s=5) -> Optional[int]:
        return_code = None
        try:
            return_code = self._process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired as te:
            self.log.warning("Timeout waiting for process expired. {}".format(te))

        return return_code

def enqueue_output(stdout, stderr, queue: Queue, logger):
    for line in iter(stdout.readline, b''):
        if len(line.strip()) > 0:
            queue.put_nowait(line)
            if logger:
                logger.debug(line)

    stdout.close()
    for line in iter(stderr.readline, b''):
        if len(line.strip()) > 0:
            queue.put_nowait(line)
            if logger:
                logger.error(line)
    stderr.close()
    time.sleep(0.5)
