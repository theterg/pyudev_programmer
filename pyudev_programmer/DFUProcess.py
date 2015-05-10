from subprocess import PIPE, Popen
from fcntl import fcntl, F_GETFL, F_SETFL
from os import O_NONBLOCK, read
from colorama import Fore, Back, Style
import sys
import time
import re
import threading

class DFUProcess(threading.Thread):
    def __init__(self, cmd, prog_callback=None):
        super(DFUProcess, self).__init__()
        self.running = True
        self.daemon = True
        self.prog_callback = prog_callback
        self.last_output = ''
        self.last_error = ''
        self.last_output_time = 0.0
        self.last_error_time = 0.0
        self.line_log = []
        self.progress = 0
        self.p = launchproc(cmd)
        self.start()

    def find_prog(self, line):
        match = re.match(r'.*\s+(\d+)%\s+.*', line)
        if match is not None:
            self.progress = int(match.groups()[0])
            if self.prog_callback is not None:
                # Send progress, but we're still running!
                self.prog_callback(self.progress, False, None)

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
        exception_encountered = None
        while(True):
            try:
                stdout = self.p.stdout.read(1)
                if len(stdout) != 0 and stdout != '\n' and stdout != '\r':
                    stdout_buf.append(stdout)
                if stdout == '\r' or stdout == '\n':
                    line = ''.join(stdout_buf).strip()
                    # Don't allow callbacks to halt the process
                    # Squash exceptions and re-raise at the end
                    try:
                        self.find_prog(line)
                        self.line_callback(line)
                    except Exception as e:
                        exception_encountered = e
                    stdout_buf = []
            except IOError:
                pass
            try:
                stderr = self.p.stderr.read(1)
                if len(stderr) != 0:
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
            code = self.p.poll()
            # Ensure we've read everything out of the pipes before quitting
            if code is not None and len(stdout) == 0 and len(stderr) == 0:
                running = False
                break
        if exception_encountered is not None:
            raise e
        if self.prog_callback is not None:
            self.prog_callback(self.progress, True, self.p.returncode)

    def stop(self):
        self.running = False
        self.join()

def launchproc(cmd):
    p = Popen([cmd], stdout=PIPE, stderr=PIPE, stdin=PIPE, shell=True)
    flags = fcntl(p.stdout, F_GETFL) # get current p.stdout flags
    fcntl(p.stdout, F_SETFL, flags | O_NONBLOCK)
    flags = fcntl(p.stderr, F_GETFL) # get current p.stdout flags
    fcntl(p.stderr, F_SETFL, flags | O_NONBLOCK)
    return p

def my_cb(prog, complete, error):
    print (prog, complete, error)
    if complete and error:
        print "Finished with error '%s', dumping log:" % (p.last_error)
        print '\n'.join(p.line_log)

p = DFUProcess('dfu-util -nR -a 0 -D /home/tergia/Downloads/ev1_release0.53.dfu', my_cb)
