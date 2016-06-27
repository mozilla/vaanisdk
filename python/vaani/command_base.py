# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
from os import path
import contextlib
import subprocess
from subprocess import PIPE
import sys
import platform
import collections

from os.path import expanduser

import toml

from mach.registrar import Registrar

BIN_SUFFIX = ".exe" if sys.platform == "win32" else ""
CMD_SUFFIX = ".cmd" if sys.platform == "win32" else ""

@contextlib.contextmanager
def cd(new_path):
    """Context manager for changing the current working directory"""
    previous_path = os.getcwd()
    try:
        os.chdir(new_path)
        yield
    finally:
        os.chdir(previous_path)

def call(*args, **kwargs):
    """Wrap `subprocess.call`, printing the command if verbose=True."""
    verbose = kwargs.pop('verbose', False)
    if verbose:
        print(' '.join(args[0]))
    # we have to use shell=True in order to get PATH handling
    # when looking for the binary on Windows
    return subprocess.call(*args, shell=sys.platform == 'win32', **kwargs)


def normalize_env(env):
    # There is a bug in subprocess where it doesn't like unicode types in
    # environment variables. Here, ensure all unicode are converted to
    # binary. utf-8 is our globally assumed default. If the caller doesn't
    # want UTF-8, they shouldn't pass in a unicode instance.
    normalized_env = {}
    for k, v in env.items():
        if isinstance(k, unicode):
            k = k.encode('utf-8', 'strict')

        if isinstance(v, unicode):
            v = v.encode('utf-8', 'strict')

        normalized_env[k] = v

    return normalized_env


def check_call(*args, **kwargs):
    """Wrap `subprocess.check_call`, printing the command if verbose=True.

    Also fix any unicode-containing `env`, for subprocess """
    verbose = kwargs.pop('verbose', False)

    if 'env' in kwargs:
        kwargs['env'] = normalize_env(kwargs['env'])

    if verbose:
        print(' '.join(args[0]))
    # we have to use shell=True in order to get PATH handling
    # when looking for the binary on Windows
    return subprocess.check_call(*args, shell=sys.platform == 'win32', **kwargs)

def show_header(verbosity):
    return verbosity > 0

def show_help(verbosity):
    return verbosity > 1

def show_progress(verbosity):
    return verbosity > 0

def show_debug(verbosity):
    return verbosity > 2

def show_result(verbosity):
    return verbosity > 0

def show_error(verbosity):
    return verbosity > 0

def print_line():
    print "*" * 100

def print_header(verbosity, title):
    if show_header(verbosity):
        print
        title = title[:78]
        print_line()
        print "*" * 10,
        print title.center(78),
        print "*" * 10
        print_line()
        print

def print_footer(verbosity):
    if show_header(verbosity):
        print_line()


class BuildNotFound(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class CommandBase(object):
    """Base class for mach command providers.

    This mostly handles configuration management, such as .vaanibuild."""

    def __init__(self, context):
        self.context = context

        def get_env_bool(var, default):
            # Contents of env vars are strings by default. This returns the
            # boolean value of the specified environment variable, or the
            # speciried default if the var doesn't contain True or False
            return {'True': True, 'False': False}.get(os.environ.get(var), default)

        def resolverelative(category, key):
            # Allow ~
            self.config[category][key] = path.expanduser(self.config[category][key])
            # Resolve relative paths
            self.config[category][key] = path.join(context.topdir,
                                                   self.config[category][key])

        if not hasattr(self.context, "bootstrapped"):
            self.context.bootstrapped = False

        if not hasattr(self.context, "shared_dir"):
            self.context.shared_dir = path.join(context.topdir, "shared")

        if not hasattr(self.context, "maven_dir"):
            self.context.maven_dir = path.join(context.shared_dir, "maven")

        if not hasattr(self.context, "m2repo_dir"):
            self.context.m2repo_dir = path.join(context.shared_dir, "m2repo")

        if not hasattr(self.context, "git_dir"):
            self.context.git_dir = path.join(context.topdir, "git")

        if not hasattr(self.context, "ws_dir"):
            self.context.ws_dir = path.join(context.topdir, "ws")

        if not hasattr(self.context, "repos"):
            self.context.repos = collections.OrderedDict([
                ( "smarthome",          "eclipse" ),
                ( "openhab-core",       "kaikreuzer" ),
                ( "openhab",            "openhab" ),
                ( "openhab2-addons",    "openhab" ),
                ( "openhab-distro",     "owner" )
            ])

        config_path = path.join(context.topdir, ".vaanibuild")
        if path.exists(config_path):
            with open(config_path) as f:
                self.config = toml.loads(f.read())
        else:
            self.config = {}

        # Handle missing/default items
        # self.config.setdefault("tools", {})

        # m2_dir = os.environ.get("M2_DIR", ".m2")
        # self.config["tools"].setdefault("m2-dir", m2_dir)
        # resolverelative("tools", "m2-dir")

        # maven_root = os.environ.get("MAVEN_ROOT", path.join("tools", "maven"))
        # self.config["tools"].setdefault("maven-root", maven_root)
        # resolverelative("tools", "maven-root")

    def build_env(self):
        """Return an extended environment dictionary."""
        env = os.environ.copy()
        if sys.platform == "win32" and type(env['PATH']) == unicode:
            # On win32, the virtualenv's activate_this.py script sometimes ends up
            # turning os.environ['PATH'] into a unicode string.  This doesn't work
            # for passing env vars in to a process, so we force it back to ascii.
            # We don't use UTF8 since that won't be correct anyway; if you actually
            # have unicode stuff in your path, all this PATH munging would have broken
            # it in any case.
            env['PATH'] = env['PATH'].encode('ascii', 'ignore')
        env['MAVEN_OPTS'] = '-Dmaven.artifact.threads=4 -Xmx2469m'
        env['MAVEN_SKIP_RC'] = 'true'

        return env

    def ensure_bootstrapped(self, target=None):
        if self.context.bootstrapped:
            return

        if not (path.exists(self.context.maven_dir)):
            print("Installing Maven")
            Registrar.dispatch("bootstrap-maven", context=self.context)

        if not (path.exists(self.context.m2repo_dir)):
            print("Preparing local Maven repository")
            Registrar.dispatch("bootstrap-m2repo", context=self.context)

        if not (path.exists(self.context.git_dir)):
            print("Fetching git repositories")
            Registrar.dispatch("bootstrap-git", context=self.context)

        self.context.bootstrapped = True
