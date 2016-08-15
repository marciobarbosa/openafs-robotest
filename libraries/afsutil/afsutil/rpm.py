# Copyright (c) 2014-2016 Sine Nomine Associates
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THE SOFTWARE IS PROVIDED 'AS IS' AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Helper to install and remove OpenAFS RPM packages."""

import logging
import os
import sys
import re
import glob
import pprint

from afsutil.system import sh, CommandFailed
from afsutil.install import Installer

logger = logging.getLogger(__name__)

def rpm(*args):
    """Helper to run the rpm command."""
    return sh('rpm', *args, output=True, quiet=True)

class RpmInstaller(Installer):
    """Helper to install and remove OpenAFS RPMs."""

    def __init__(self, dir=None, **kwargs):
        Installer.__init__(self, **kwargs)
        if dir is None:
            dir = os.getcwd()
        self.pkgdir = dir  # Defer checks until needed.
        self.packages = None
        self.installed = None

    def find_installed(self):
        """Find the installed openafs packages on this system."""
        # We get all of packages and check the names here since the rpm
        # command on this system could be old and not support wildcards.
        self.installed = {}
        output = rpm('--query', '--all',
                     '--queryformat', '%{NAME} %{VERSION} %{RELEASE} %{ARCH}\\n')
        for line in output:
            name,version,release,arch = line.split()
            if name.startswith('kmod-openafs') or name.startswith('openafs'):
                self.installed[name] = {
                    'version': version,
                    'release': release,
                    'arch': arch}
        return self.installed

    def find_packages(self):
        """Find the OpenAFS rpm package files in the package directory."""
        # Older versions of this tried to parse the filenames to get package
        # attributes. This version uses rpm query in instead, which seems to
        # to be less error prone.  We build a list instead of a dict, since
        # there could be more than one rpm per package name, e.g.,
        # kmod_openafs*.
        if self.packages is not None:
            return self.packages  # Scan the first time needed.
        if not os.path.isdir(self.pkgdir):
            raise AssertionError("Cannot find pkgdir directory '%s'!" % self.pkgdir)
        self.packages = []
        files = glob.glob(os.path.join(self.pkgdir, '*.rpm'))
        for file in files:
            # Skip the source rpm, if present.
            if file.endswith('.src.rpm'):
                continue
            output = rpm('--query', '--package', file,
                         '--queryformat', '%{NAME} %{VERSION} %{RELEASE} %{ARCH}\\n')
            name,version,release,arch = output[0].split()
            self.packages.append({'file': file, 'name': name, 'version': version,
                                  'release': release, 'arch': arch})
        if len(self.packages) == 0:
            raise AssertionError("No packages found in directory '%s'" % self.pkgdir)
        return self.packages

    def find_package(self, name):
        """Get a package rpm file by package name."""
        # To simplify, assume we will not mix different versions of userspace
        # rpms in the package directory.
        packages = self.find_packages()
        found = []
        for p in packages:
            if p['name'] == name:
                found.append(p)
        if len(found) == 0:
            raise AssertionError("Package '%s' not found in '%s'." % (name, self.pkgdir))
        if len(found) > 1:
            raise AssertionError("Multiple packages for '%s' found in '%s'." % (name, self.pkgdir))
        return found[0]

    def find_kmod(self):
        """Find the kmod package matching the kernel version on this system."""
        # This functions handles rhel/centos openafs kmod naming.  The release
        # name in the kmod contains the kernel version number without the
        # system arch.  Convert the underscore in the package release to a dash
        # to match the kernel's version format.
        kernel = os.uname()[2]  # e.g. '2.6.32-431.29.2.el6.x86_64'
        logger.info("Searching for module package for kernel version %s.", kernel)
        packages = self.find_packages()
        for p in packages:
            if p['name'].startswith('kmod-openafs'):
                arch = p['arch']  #  e.g., 'x86_64'
                release = p['release'].replace('_', '-') # e.g. '1.2.6.32_431.29.2.el6'
                release = ".".join((release, arch))
                if release.find(kernel) != -1:
                    return p  # kernel version found
        raise AssertionError("Cannot find module package for kernel version %s." % (kernel,))

    def install(self):
        """Install RPM packages."""
        self.pre_install()
        if not (self.do_server or self.do_client):
            raise AssertionError("Expected client and/or server component.")
        packages = []
        packages.append(self.find_package('openafs'))
        packages.append(self.find_package('openafs-krb5'))
        packages.append(self.find_package('openafs-docs'))
        if self.do_server:
            packages.append(self.find_package('openafs-server'))
        if self.do_client:
            packages.append(self.find_package('openafs-client'))
            packages.append(self.find_kmod())
        files = []
        for p in packages:
            file = p['file']
            files.append(file)
            logger.info("Installing %s.", file)
        if len(files) == 0:
            raise AssertionError("No rpm files found to install.")
        rpm('-v', '--install', '--replacefiles', '--replacepkgs', *files)
        self.post_install()

    def remove(self):
        """Remove OpenAFS RPM packages."""
        # Remove all packages by default. Optionaly remove just the server or
        # client packages. If removing just one component and the other is not
        # present, then also remove the common packages.
        self.pre_remove()
        installed = self.find_installed().keys()
        packages = [] # names of packages to be removed
        if self.do_server and self.do_client:
            packages = installed # remove everything
        elif self.do_server:
            if 'openafs-client' not in installed:
                packages = installed              # remove common too
            elif 'openafs-server' in installed:
                packages = ['openafs-server']
        elif self.do_client:
            if 'openafs-server' not in installed:
                packages = installed              # remove common too
            elif 'openafs-client' in installed:
                packages = ['openafs-client', 'kmod-openafs']
        if packages:
            logger.info("removing %s" % " ".join(packages))
            rpm('-v', '--erase', *packages)
        self.post_remove()

#
# Test driver.
#
class _Test(object):
    def __init__(self, pkgdir):
        self.pkgdir = pkgdir

    def test_find_installed(self):
        i = RpmInstaller()
        installed = i.find_installed()
        print "installed:"
        pprint.pprint(installed)

    def test_find_packages(self):
        i = RpmInstaller(pkgdir=self.pkgdir)
        packages = i.find_packages()
        print "packages:"
        pprint.pprint(packages)

    def test_find_package(self):
        i = RpmInstaller(pkgdir=self.pkgdir)
        package = i.find_package('openafs')
        print "openafs package:"
        pprint.pprint(package)

    def test_find_kmod(self):
        i = RpmInstaller(pkgdir=self.pkgdir)
        package = i.find_kmod()
        print "kmod package:"
        pprint.pprint(package)

    def test_install(self):
        i = RpmInstaller(pkgdir=self.pkgdir)
        i.install()

    def test_remove(self):
        i = RpmInstaller(pkgdir=self.pkgdir)
        i.remove()

    def test_install_server(self):
        i = RpmInstaller(pkgdir=self.pkgdir, components=['server'])
        i.install()

    def test_remove_server(self):
        i = RpmInstaller(pkgdir=self.pkgdir, components=['server'])
        i.remove()

    def test_install_client(self):
        i = RpmInstaller(pkgdir=self.pkgdir, components=['client'])
        i.install()

    def test_remove_client(self):
        i = RpmInstaller(pkgdir=self.pkgdir, components=['client'])
        i.remove()

    def test(self):
        logging.basicConfig(level=logging.DEBUG)
        self.test_find_installed()
        self.test_find_packages()
        self.test_find_package()
        self.test_find_kmod()
        self.test_install()
        self.test_remove()
        self.test_install_server()
        self.test_install_client()
        self.test_remove_server() # leaves common packages
        self.test_find_installed()
        self.test_remove_client() # removes common packages
        self.test_find_installed()

def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: python rpm.py <pkgdir>\n")
        sys.exit(1)
    if os.geteuid() != 0:
        sys.stderr.write("Must run as root!\n")
        sys.exit(1)
    t = _Test(sys.argv[1])
    t.test()

if __name__ == '__main__':
    main()
