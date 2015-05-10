from subprocess import PIPE, Popen
from fcntl import fcntl, F_GETFL, F_SETFL
from os import O_NONBLOCK, read
from colorama import Fore, Back, Style
import sys
import time
import re
import threading

class DFUProcess(threading.Thread):
    def __init__(self, cmd, serial=None, prog_callback=None, idle_delay=0.1):
        ''' Launch a new DFU Process - execute CMD immediately

        CMD will be launched via Popen and both it's stdout and stderr polled.
        Any lines (terminated with \\r or \\n) will be consumed and added to
        the line_log, as well as available via last_output and last_error.
        stdout will be examined for a " XX% " -> any percentage surrounded by spaces.
        Status will be returned in a callback (prog_callback) as it's produced.

        :param cmd: A string command to execute - the DFU deploy command
        :param serial: (optional) The serial number associated with the device
        :param prog_callback: (optional) a callback function with signature:
                              callback(process, progress, complete, error)
                              where process is a reference to this object
                              progress is an integer percentage of the progress
                              complete is whether the DFU command has returned
                              error is it's system return code
        :param idle_delay: If no data was returned on stdout or sterr, sleep for this long
                           Since stdout/stderr are configured as non-blocking, we need to
                           sleep for a short while to reduce CPU utilization
        '''
        super(DFUProcess, self).__init__()
        self.running = True
        self.daemon = True
        self.serial = serial
        self.prog_callback = prog_callback
        self.last_output = ''
        self.last_error = ''
        self.idle_delay = idle_delay
        self.last_output_time = 0.0
        self.last_error_time = 0.0
        self.line_log = []
        self.progress = 0
        self.returncode = None
        self.p = launchproc(cmd)
        # Will actually launch a new thread, executing run()
        self.start()

    def find_prog(self, line):
        match = re.match(r'.*\s+(\d+)%\s+.*', line)
        if match is not None:
            self.progress = int(match.groups()[0])
            if self.prog_callback is not None:
                # Send progress, but we're still running!
                self.prog_callback(self, self.progress, False, None)

    def line_callback(self, line):
        self.last_output = line
        self.last_output_time = time.time()
        self.line_log.append(line)

    def err_callback(self, line):
        self.last_error = line
        self.last_error_time = time.time()
        self.line_log.append(line)

    def run(self):
        stdout_buf = []
        stderr_buf = []
        stdout = ''
        stderr = ''
        exception_encountered = None
        # Run loop as long as child process is alive
        while(True):
            # Try to read byte from stdout - IOError triggered if none available
            try:
                stdout = self.p.stdout.read(1)
                if len(stdout) != 0 and stdout != '\n' and stdout != '\r':
                    # Filter out \r and \n from the stream
                    stdout_buf.append(stdout)
                if stdout == '\r' or stdout == '\n':
                    line = ''.join(stdout_buf).strip()
                    # Don't allow callbacks to halt the process!
                    # Squash exceptions and re-raise at the end
                    try:
                        self.find_prog(line)
                        self.line_callback(line)
                    except Exception as e:
                        exception_encountered = e
                    stdout_buf = []
            except IOError:
                pass
            # Try to read byte from stderr - IOError triggered if none available
            try:
                stderr = self.p.stderr.read(1)
                if len(stderr) != 0 and stderr != '\n' and stderr != '\r':
                    # Filter out \r and \n from the stream
                    stderr_buf.append(stderr)
                if stderr == '\r' or stderr == '\n':
                    # Don't allow callbacks to halt the process
                    # Squash exceptions and re-raise at the end
                    try:
                        self.err_callback(''.join(stderr_buf))
                    except Exception as e:
                        exception_encountered = e
                    stderr_buf = []
            except IOError:
                pass
            # Check if child has exited yet
            self.returncode = self.p.poll()
            # Ensure we've read everything out of the pipes before quitting
            if self.returncode is not None and len(stdout) == 0 and len(stderr) == 0:
                running = False
                break
            # Rest this thread if both pipes are empty
            # Otherwise we busy-loop quite a bit...
            if len(stdout) == 0 and len(stderr) == 0:
                time.sleep(self.idle_delay)
        # Inform listener that we've completed
        if self.prog_callback is not None:
            self.prog_callback(self, self.progress, True, self.returncode)
        # Now re-raise any exceptions we've encountered
        if exception_encountered is not None:
            raise e

    def stop(self):
        self.running = False
        self.join()

def launchproc(cmd):
    ''' Execute cmd in a shell, route stdout/stderr/stdin to pipes, 
    configure pipes as non-blocking.
    NOTE - this may not port well to windows, but there's no easy way to
    configure pipes as non-blocking otherwise...'''
    p = Popen([cmd], stdout=PIPE, stderr=PIPE, stdin=PIPE, shell=True)
    flags = fcntl(p.stdout, F_GETFL) # get current p.stdout flags
    fcntl(p.stdout, F_SETFL, flags | O_NONBLOCK)
    flags = fcntl(p.stderr, F_GETFL) # get current p.stdout flags
    fcntl(p.stderr, F_SETFL, flags | O_NONBLOCK)
    return p

