# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals

import base64
import json
import os
import os.path as path
import re
import shutil
import sys
import StringIO
import tarfile
import urllib2
import errno



from vaani.command_base import *

from mach.decorators import (
    CommandArgument,
    CommandProvider,
    Command,
    SubCommand
)

def download(desc, src, writer, start_byte=0):
    if start_byte:
        print("Resuming download of %s..." % desc)
    else:
        print("Downloading %s..." % desc)
    dumb = (os.environ.get("TERM") == "dumb") or (not sys.stdout.isatty())

    try:
        if start_byte:
            src = urllib2.Request(src, headers={'Range': 'bytes={}-'.format(start_byte)})
        resp = urllib2.urlopen(src)

        fsize = None
        if resp.info().getheader('Content-Length'):
            fsize = int(resp.info().getheader('Content-Length').strip()) + start_byte

        recved = start_byte
        chunk_size = 8192

        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            recved += len(chunk)
            if not dumb:
                if fsize is not None:
                    pct = recved * 100.0 / fsize
                    print("\rDownloading %s: %5.1f%%" % (desc, pct), end="")

                sys.stdout.flush()
            writer.write(chunk)

        if not dumb:
            print()
    except urllib2.HTTPError, e:
        print("Download failed (%d): %s - %s" % (e.code, e.reason, src))
        if e.code == 403:
            print("No maven compiler binary available for this platform. "
                  "Please see https://github.com/mozilla/vaanisdk/#prerequisites")
        sys.exit(1)
    except urllib2.URLError:
        print("Error downloading; are you connected to the internet?")
        sys.exit(1)
    except KeyboardInterrupt:
        writer.flush()
        raise


def download_file(desc, src, dst):
    tmp_path = dst + ".part"
    try:
        start_byte = os.path.getsize(tmp_path)
        with open(tmp_path, 'ab') as fd:
            download(desc, src, fd, start_byte=start_byte)
    except os.error:
        with open(tmp_path, 'wb') as fd:
            download(desc, src, fd)
    os.rename(tmp_path, dst)


def download_bytes(desc, src):
    content_writer = StringIO.StringIO()
    download(desc, src, content_writer)
    return content_writer.getvalue()


def extract(src, dst, movedir=None):
    tarfile.open(src).extractall(dst)

    if movedir:
        for f in os.listdir(movedir):
            frm = path.join(movedir, f)
            to = path.join(dst, f)
            os.rename(frm, to)
        os.rmdir(movedir)

    os.remove(src)

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

@CommandProvider
class MachCommands(CommandBase):
    @Command('env',
             description='Print environment setup commands',
             category='bootstrap')
    def env(self):
        env = self.build_env()
        print("export PATH=%s" % env["PATH"])
        if sys.platform == "darwin":
            print("export DYLD_LIBRARY_PATH=%s" % env["DYLD_LIBRARY_PATH"])
        else:
            print("export LD_LIBRARY_PATH=%s" % env["LD_LIBRARY_PATH"])

    @Command('wipe-all',
             description='Wipe everything that was bootstrapped (including clones of all git repositories)',
             category='bootstrap')
    def wipe_all(self):
        if path.isdir(self.context.shared_dir):
            shutil.rmtree(self.context.shared_dir)
        if path.isdir(self.context.git_dir):
            shutil.rmtree(self.context.git_dir)
        print("Unbootstrapping done.")

    @Command('bootstrap-maven',
             description='Download the Maven build tool',
             category='bootstrap')
    @CommandArgument('--force', '-f',
                     action='store_true')
    @CommandArgument('--verbosity', '-v',
                     default=2)
    def bootstrap_maven(self, force=False, verbosity=2):
        print_header(verbosity, 'Bootstrapping Maven')
        maven_dir = self.context.maven_dir

        if not force and path.exists(maven_dir):
            print("Maven already downloaded.", end=" ")
            print("Use |bootstrap-maven --force| to download again.")
        else:
            if path.isdir(maven_dir):
                shutil.rmtree(maven_dir)

            maven_url = "http://www-eu.apache.org/dist/maven/maven-3/3.3.9/binaries/apache-maven-3.3.9-bin.tar.gz"
            mkdir_p(self.context.shared_dir)
            tgz_file = path.join(self.context.shared_dir, "maven.tar.gz")

            download_file("Maven", maven_url, tgz_file)

            print("Extracting Maven...")
            extract(tgz_file, self.context.shared_dir)
            os.rename(path.join(self.context.shared_dir, 'apache-maven-3.3.9'), maven_dir)
        print_footer(verbosity)

    @Command('bootstrap-m2repo',
             description='Prepopulate local Maven repository',
             category='bootstrap')
    @CommandArgument('--force', '-f',
                     action='store_true')
    @CommandArgument('--verbosity', '-v',
                     default=2)
    def bootstrap_m2repo(self, force=False, verbosity=2):
        print_header(verbosity, 'Bootstrapping local maven repository')
        m2repo_dir = self.context.m2repo_dir

        if not force and path.exists(m2repo_dir):
            print("Maven repository already prepopulated.", end=" ")
            print("Use |bootstrap-m2repo --force| to download again.")
        else:
            if path.isdir(m2repo_dir):
                shutil.rmtree(m2repo_dir)
            os.makedirs(m2repo_dir)

            latestPage = urllib2.urlopen('https://github.com/mozilla/openhab2-addons/releases/latest').read()
            m2repo_url = 'https://github.com/mozilla/openhab2-addons/releases/download/0.1.0t9/m2repository.tar.gz'
            result = re.search('(/mozilla/openhab2-addons/releases/download/.*/m2repository.tar.gz)', latestPage, re.IGNORECASE)
            if result:
                m2repo_url = 'https://github.com' + result.group(1)
                print (m2repo_url)
            tgz_file = path.join(self.context.shared_dir, "m2repository.tar.gz")

            download_file("Maven repository", m2repo_url, tgz_file)

            print("Extracting Maven repository...")
            extract(tgz_file, m2repo_dir)
        print_footer(verbosity)

    @Command('bootstrap-git',
             description='Clone and prepare git repositories',
             category='bootstrap')
    @CommandArgument('repository')
    @CommandArgument('--force', '-f',
                     action='store_true')
    @CommandArgument('--verbosity', '-v',
                     default=2)
    def bootstrap_git(self, repository='all', force=False, verbosity=2):
        print_header(verbosity, 'Bootstrapping git repositories')
        show_force = False
        if repository == 'all':
            repos = self.context.repos
        else:
            repos = [repository]
        for repo in repos:
            repo_dir = path.join(self.context.git_dir, repo)
            if not force and path.exists(repo_dir):
                if show_help(verbosity):
                    print ("Git repository " + repo + " is already prepared.")
                    if len(repos) == 1:
                        print("Use |bootstrap-git " + repo + " --force| to wipe, clone and prepare again.")
                    else:
                        show_force = True
            else:
                if path.isdir(repo_dir):
                    shutil.rmtree(repo_dir)
                os.makedirs(repo_dir)
                call(["git", "clone", "https://github.com/mozilla/" + repo],
                            env=self.build_env(), cwd=self.context.git_dir)
        if show_force and show_help(verbosity):
            print("Some repository directories were already existing. You can use |bootstrap-git --force| to also wipe, clone and prepare those.")
        print_footer(verbosity)

    @Command('bootstrap',
             description='Bootstrap the whole project',
             category='bootstrap')
    @CommandArgument('--force', '-f',
                     action='store_true')
    @CommandArgument('--verbosity', '-v',
                     default=2)
    def bootstrap(self, force=False, verbosity=2):
        self.bootstrap_git(force=force, verbosity=verbosity)
        self.bootstrap_maven(force=force)
        self.bootstrap_m2repo(force=force)
