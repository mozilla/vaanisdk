# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals

import datetime
import os
import os.path as path
import sys
import shutil
from time import time

from time import time

from mach.decorators import (
    CommandArgument,
    CommandProvider,
    Command,
)

from vaani.command_base import *

def notify_linux(title, text):
    try:
        import dbus
        bus = dbus.SessionBus()
        notify_obj = bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
        method = notify_obj.get_dbus_method("Notify", "org.freedesktop.Notifications")
        method(title, 0, "", text, "", [], {"transient": True}, -1)
    except:
        raise Exception("Optional Python module 'dbus' is not installed.")


def notify_win(title, text):
    from ctypes import Structure, windll, POINTER, sizeof
    from ctypes.wintypes import DWORD, HANDLE, WINFUNCTYPE, BOOL, UINT

    class FLASHWINDOW(Structure):
        _fields_ = [("cbSize", UINT),
                    ("hwnd", HANDLE),
                    ("dwFlags", DWORD),
                    ("uCount", UINT),
                    ("dwTimeout", DWORD)]

    FlashWindowExProto = WINFUNCTYPE(BOOL, POINTER(FLASHWINDOW))
    FlashWindowEx = FlashWindowExProto(("FlashWindowEx", windll.user32))
    FLASHW_CAPTION = 0x01
    FLASHW_TRAY = 0x02
    FLASHW_TIMERNOFG = 0x0C

    params = FLASHWINDOW(sizeof(FLASHWINDOW),
                         windll.kernel32.GetConsoleWindow(),
                         FLASHW_CAPTION | FLASHW_TRAY | FLASHW_TIMERNOFG, 3, 0)
    FlashWindowEx(params)


def notify_darwin(title, text):
    try:
        import Foundation

        bundleDict = Foundation.NSBundle.mainBundle().infoDictionary()
        bundleIdentifier = 'CFBundleIdentifier'
        if bundleIdentifier not in bundleDict:
            bundleDict[bundleIdentifier] = 'mach'

        note = Foundation.NSUserNotification.alloc().init()
        note.setTitle_(title)
        note.setInformativeText_(text)

        now = Foundation.NSDate.dateWithTimeInterval_sinceDate_(0, Foundation.NSDate.date())
        note.setDeliveryDate_(now)

        centre = Foundation.NSUserNotificationCenter.defaultUserNotificationCenter()
        centre.scheduleNotification_(note)
    except ImportError:
        raise Exception("Optional Python module 'pyobjc' is not installed.")


def notify_build_done(elapsed):
    """Generate desktop notification when build is complete and the
    elapsed build time was longer than 30 seconds."""
    if elapsed > 30:
        notify("Vaani build", "Completed in %s" % str(datetime.timedelta(seconds=elapsed)))


def notify(title, text):
    """Generate a desktop notification using appropriate means on
    supported platforms Linux, Windows, and Mac OS.  On unsupported
    platforms, this function acts as a no-op."""
    platforms = {
        "linux": notify_linux,
        "linux2": notify_linux,
        "win": notify_win,
        "darwin": notify_darwin
    }
    func = platforms.get(sys.platform)

    if func is not None:
        try:
            func(title, text)
        except Exception as e:
            extra = getattr(e, "message", "")
            print("[Warning] Could not generate notification! %s" % extra, file=sys.stderr)


@CommandProvider
class MachCommands(CommandBase):

    @Command('clean',
             description='Clean repositories',
             category='build')
    @CommandArgument('repository')
    @CommandArgument('--verbosity', '-v',
                     default=2)
    def clean(self, repository='all', verbosity=2):
        self.maven(repository, "clean", "Cleaning", verbosity)

    @Command('build',
             description='Build one repository by specifying its name ("smarthome", "openhab-core", "openhab", "openhab2-addons", "openhab-distro") or all repositories in the right order by keyword "all".',
             category='build')
    @CommandArgument('repository')
    @CommandArgument('--verbosity', '-v',
                     default=2)
    def build(self, repository='all', verbosity=2):
        self.maven(repository, "install", "Building", verbosity)

    def maven(self, repository, command, verb, verbosity=2):
        self.ensure_bootstrapped()
        opts = ["-Dmaven.repo.local=" + self.context.m2repo_dir]
        if not verbosity:
            opts += ["-q"]
        if repository == 'all':
            repos = self.context.repos
        else:
            repos = [repository]
        start_time = time()
        for repo in repos:
            print_header(verbosity, verb + " " + repo)
            repo_dir = path.join(self.context.git_dir, repo)
            call(["mvn", command] + opts, env=self.build_env(), cwd=repo_dir, verbose=verbosity > 2)
            print_footer(verbosity)
        elapsed = time() - start_time
        print_header(verbosity, "Completed in %s" % str(datetime.timedelta(seconds=elapsed)))
        if show_result(verbosity):
            notify_build_done(elapsed)
