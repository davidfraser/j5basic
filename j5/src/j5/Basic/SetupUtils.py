# -*- coding: utf-8 -*-

"""Module for tools for easing creating setup files"""

import os
import fnmatch
from distutils import log

class fileset(list):
    """this is a installation list of a set of files from a directory"""
    def __init__(self, src, dest, destsubdir, exclude=["CVS", ".svn"], include=None):
        """creates the fileset by walking through src directory"""
        self.src = src
        self.dest = dest
        self.destsubdir = destsubdir
        self.exclude = exclude
        self.include = include
        # this calls self.adddirfiles(None, dirname, names) for each subdirectory dirname of self.src
        os.path.walk(self.src, self.adddirfiles, None)

    def adddirfiles(self, arg, dirname, names):
        """adds the files names from dirname to self (which is a list)"""
        # arg is ignored
        filenames = []
        for exclude in self.exclude:
            for name in fnmatch.filter(names, exclude):
                names.remove(name)
        if self.include is not None:
            filtered_names = []
            for include in self.include:
                filtered_names.extend(fnmatch.filter(names, include))
            names = filtered_names
        for name in names:
            filename = os.path.join(dirname,name)
            if not os.path.isdir(filename):
                filenames.append(filename)
        if len(filenames) > 0:
            destsubdirname = dirname.replace(self.src,self.destsubdir,1)
            destpath = os.path.join(self.dest,destsubdirname)
            self.append((destpath,filenames))

############# remove_source alterations to distutils ############

def extend_function(orig_function, extended_function):
    def wrapped_function(*args, **kwargs):
        result = orig_function(*args, **kwargs)
        result = extended_function(result, *args, **kwargs)
        return result
    return wrapped_function

def is_removable (py_file):
    """Checks whether a given python file should be removed.
    This version removes all sjsoft python files"""
    parts = py_file.split(os.sep)
    cutpoints = ["site-packages", "build", "lib"]
    while True in [cutpoint in parts for cutpoint in cutpoints]:
        for cutpoint in cutpoints:
            if cutpoint in parts:
                parts = parts[parts.index(cutpoint)+1:]
    py_file = os.sep.join(parts)
    if building_standalone:
        return False
    return "sjsoft" in parts

def remove_source (py_files, verbose=1, dry_run=0):
    """Remove the original source for a collection of Python source files
    (assuming they have been compiled to either .pyc or .pyo form).
    'py_files' is a list of files to remove; any files that don't end in
    ".py" are silently skipped.

    If 'verbose' is true, prints out a report of each file.  If 'dry_run'
    is true, doesn't actually do anything that would affect the filesystem.

    """
    for file in py_files:
        if file[-3:] != ".py":
            # This lets us be lazy and not filter filenames in
            # the "install_lib" command.
            continue
        if not os.path.exists(file+"c") or os.path.exists(file+"o"):
            log.warn("compiled file does not exist for %s" % (file))
        if os.path.exists(file) and is_removable(file):
            log.info("removing source file %s" % (file))
            if not dry_run:
                os.remove(file)

def bdist_get_inidata_removesource(result, self):
    return result + "\nremove_source=%d" % (self.remove_source)

# in run, set install_lib.remove_source (and compile) appropriately
def reinitialize_command_removesource(result, self, command, reinit_subcommands=0):
    if command == "install_lib":
        # pass the remove_source argument on to install_lib
        result.remove_source = self.remove_source
    return result

def make_finalize_options_removesource(command_source):
    """makes an extender method for getting the removesource option from the given command name"""
    def finalize_options_removesource(result, self):
        self.set_undefined_options(command_source, ('remove_source', 'remove_source'))
        return result
    return finalize_options_removesource

def byte_compile_removesource(self, files):
    if self.remove_source and not (self.compile or self.optimize > 0):
        self.compile = 1
    self.byte_compile_orig(files)
    if self.remove_source:
        remove_source(files, verbose=self.verbose, dry_run=self.dry_run)

def get_outputs_removesource(result, self):
    if self.remove_source:
        filtered_result = []
        for filename in result:
            if filename.endswith(".pycc"):
                continue
            elif filename.endswith(".py"):
                if not is_removable(filename):
                    filtered_result.append(filename)
            else:
                filtered_result.append(filename)
        return filtered_result
    else:
        return result

def initialize_remove_source(result, self):
    self.remove_source = None
    return result

def allow_distutils_remove_source():
    """adds the remove_source capabilities to distutils"""
    from distutils import util
    util.remove_source = remove_source
    option = ('remove-source', None, "don't include original .py source files (remove from distribution)")
    option_passing = {"build_py": "build", "install_lib": "install"}

    def add_remove_source_option(commandclass):
        commandclass.user_options.append(option)
        commandclass.boolean_options.append('remove-source')
        commandclass.initialize_options = extend_function(commandclass.initialize_options, initialize_remove_source)
        if hasattr(commandclass, "byte_compile"):
            commandclass.byte_compile_orig = commandclass.byte_compile
            commandclass.byte_compile = byte_compile_removesource
        if commandclass.__name__ in option_passing:
            finalize_options_removesource = make_finalize_options_removesource(option_passing[commandclass.__name__])
            commandclass.finalize_options = extend_function(commandclass.finalize_options, finalize_options_removesource)

    # bdist_wininst changes
    from distutils.command import bdist_wininst
    wininst = bdist_wininst.bdist_wininst
    add_remove_source_option(wininst)
    wininst.reinitialize_command = extend_function(wininst.reinitialize_command, reinitialize_command_removesource)
    wininst.get_inidata = extend_function(wininst.get_inidata, bdist_get_inidata_removesource)
    # bdist_rpm changes
    from distutils.command import bdist_rpm
    add_remove_source_option(bdist_rpm.bdist_rpm)
    # build changes
    from distutils.command import build
    add_remove_source_option(build.build)
    from distutils.command import build_py
    add_remove_source_option(build_py.build_py)
    # install changes
    from distutils.command import install
    add_remove_source_option(install.install)
    from distutils.command import install_lib
    libinst = install_lib.install_lib
    add_remove_source_option(libinst)
    libinst.get_outputs = extend_function(libinst.get_outputs, get_outputs_removesource)

