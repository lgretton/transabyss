#!/usr/bin/env python

# written by Ka Ming Nip
# updated on September 5, 2014
# Copyright 2014 Canada's Michael Smith Genome Sciences Centre

import argparse
import math
import os
import sys
import time
from functools import partial
from multiprocessing.dummy import Pool
from subprocess import call
from utilities import package_info

class StopWatch:
    """A timer class that reports the elapsed time.
    """
    
    start = None
    
    def __init__(self):
        """Create and start the stopwatch.
        """
        self.start = time.time()
    #enddef
    
    def stop(self):
        """Returns the elapsed time since the stop watch's existence.
        """
        
        elapsed = time.time() - self.start
        return convert_hms(elapsed)
    #enddef
#endclass

def log(info):
    """Print the message to STDOUT.
    """

    print info
    sys.stdout.flush()
#enddef

def convert_hms(seconds):
    """Convert the number of seconds to hours, minutes, seconds.
    """
    
    remain = int(math.floor(seconds))
    h = int(math.floor(remain/3600))
    remain -= h*3600
    m = int(math.floor(remain/60))
    remain -= m*60
    s = remain
    return h, m, s
#enddef

def run_shell_cmd(cmd):
    """Run the shell command.
    """
    
    cmd = 'bash -euo pipefail -c \'%s\'' % cmd
    
    log('CMD: ' + cmd)
    
    # start
    stopwatch = StopWatch()
    
    # execute the shell command
    return_code = call(cmd, shell=True)
    
    # stop
    h, m, s = stopwatch.stop()
    
    if h > 0 or m > 0 or s > 5:
        log('Elapsed time: %d h %d m %d s' % (h, m, s))
    #endif
    
    if return_code != 0:
        log('ERROR: CMD ended with status code %d' % return_code)
        sys.exit(return_code)
    #endif
#enddef

def run_multi_shell_cmds(cmds, max_parallel=2):
    """Run multiple shell commands in parallel.
    """
    
    for i in range(len(cmds)):
        cmds[i] = 'bash -euo pipefail -c \'%s\'' % cmds[i]
    #endfor
        
    stopwatch = StopWatch()
    
    # Based on: http://stackoverflow.com/questions/14533458/python-threading-multiple-bash-subprocesses
    pool = Pool(max_parallel)
    for i, return_code in enumerate(pool.imap(partial(call, shell=True), cmds)):        
        if return_code != 0:
            log('CMD: ' + cmds[i])
            log('ERROR: CMD ended with status code %d' % return_code)
            sys.exit(return_code)
        #endif
    #endfor
    
    h, m, s = stopwatch.stop()
    if h > 0 or m > 0 or s > 5:
        log('Elapsed time: %d h %d m %d s' % (h, m, s))
    #endif
#enddef

def is_empty_txt(path, min_non_empty_lines=1):
    """Check if the file has the specified minimum number of lines.
    """
    
    counter = 0
    with open(path, 'r') as fh:
        for line in fh:
            if len(line.strip()) > 0:
                counter += 1
                if counter >= min_non_empty_lines:
                    return False
                #endif
            #endif
        #endfor
    #endwith
    
    return counter < min_non_empty_lines
#enddef

def touch(path, times=None):
    """Touch the file.
    """
    
    with open(path, 'a'):
        os.utime(path, times)
    #endwith
#enddef

def threshold_action(threshold, inequality='>='):
    """Action performed for thresholding argparse numeric arguments.
    """

    class CustomAction(argparse.Action):
        def __call__(self, parser, namespace, value, option_string=None):
            if inequality == '>=':
                if value < threshold:
                    parser.error("value for '%s' must be >= %s" % (option_string, str(threshold)))
                #endif
            elif inequality == '>':
                if value <= threshold:
                    parser.error("value for '%s' must be > %s" % (option_string, str(threshold)))
                #endif
            elif inequality == '<':
                if value >= threshold:
                    parser.error("value for '%s' must be < %s" % (option_string, str(threshold)))
                #endif
            elif inequality == '<=':
                if value > threshold:
                    parser.error("value for '%s' must be <= %s" % (option_string, str(threshold)))
                #endif
            else:
                parser.error("cannot evaluate inequality '%s %s %s' for option '%s'" % (str(value), inequality, str(threshold), option_string))
            #endif
            setattr(namespace, self.dest, value)
        #enddef
    #endclass
    
    return CustomAction
#enddef

def path_action(check_exist=False):
    """Action performed for argparse single path argument.
    """

    class PathAction(argparse.Action):
        def __call__(self, parser, namespace, value, option_string=None):
            if check_exist and not os.path.exists(value):
                parser.error('No such file or directory %s' % value)
            #endif
            setattr(namespace, self.dest, os.path.abspath(value))
        #enddef
    #endclass
    
    return PathAction
#enddef

def paths_action(check_exist=False):
    """Action performed for argparse multiple path arguments.
    """

    class PathsAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            for i, v in enumerate(values):
                if check_exist and not os.path.exists(v):
                    parser.error('No such file or directory %s' % v)
                #endif
                values[i] = os.path.abspath(v)
            #endfor
            setattr(namespace, self.dest, values)
        #enddef
    #endclass
    
    return PathsAction
#enddef

def is_exe(fpath):
    """Check if the file at path is an executable
    """
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
#enddef        

def unix_which(program):
    """The UNIX `which' command implemented in Python.
    based on: http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
    """

    fpath, fname = os.path.split(program)
    if len(fpath) > 0:
        # has a parent directory; therefore `program' is a path
    
        if is_exe(program):
            return program
        #endif
    else:
        # `program' is a name
    
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
            #endif
        #endfor
    #endif
    
    return None
#enddef

def find_exes(program_list):
    found = {}
    missing = []

    for program in program_list:
        program_path = unix_which(program)
        if program_path is None or len(program_path) == 0:            
            missing.append(program)
        else:
            found[program] = program_path
        #endif
    #endfor
    
    return found, missing
#enddef

def check_env(executables=None, scripts=None):
    okay = True
    
    # Check whether required paths can be evaluated appropriately
    if os.path.isdir(package_info.PACKAGEDIR):
        log('Found Trans-ABySS directory at: ' + package_info.PACKAGEDIR)
    else:
        log('No such directory: ' + package_info.PACKAGEDIR)
        okay = False
    #endif
    
    if os.path.isdir(package_info.BINDIR):
        log('Found Trans-ABySS `bin` directory at: ' + package_info.BINDIR)
    else:
        log('No such directory: ' + package_info.BINDIR)
        okay = False
    #endif
    
    if not scripts is None and len(scripts) > 0:
        for script_path in scripts:
            if os.path.isfile(script_path):
                log('Found script at: ' + script_path)
            else:
                log('No such file: ' + script_path)
                okay = False
            #endif
        #endfor
    #endif
    
    # Check whether required executables are accessible
    if not executables is None and len(executables) > 0:
        found_exes, missing_exes = find_exes(executables)
        
        # List the accessible programs    
        for program, program_path in found_exes.iteritems():
            log('Found `%s\' at %s' % (program, program_path))
        #endfor
        
        # List the inaccessible programs and quit
        num_missing_exes = len(missing_exes)
        if num_missing_exes > 0:
            log('The following executables (%s) are not accessible from the PATH environment variable:\n%s' % (num_missing_exes, '\n'.join(missing_exes)) )
            okay = False
        #endif
    #endif
    
    return okay
#endef

#EOF
