"""Check that every gpgkey= in a built repofile points at a file that ships.

A gpgkey path is a plain string in a .repo file, so nothing connects it to the
place the Makefile installs keys. When leapp-repository 0.24.0 moved the trusted
key tree from common/files/rpm-gpg/<major> to
common/files/distro/<distro>/rpm-gpg/<major>, the keys moved and the repofiles
did not - dnf then failed the *target* transaction with

    Curl error (37): Couldn't read a file:// file for file:///etc/leapp/...

which names neither the repofile nor the package it was about, and only happens
once a real upgrade reaches the target repositories.

Paths under /etc/pki are the source system's own and are not checked: they are
installed by cloudlinux-release, not by this package.
"""
from __future__ import print_function

import os
import re
import sys

GPGKEY_RE = re.compile(r'^\s*gpgkey\s*=\s*(.+?)\s*$', re.MULTILINE)
LEAPP_PREFIX = '/etc/leapp/'


def iter_leapp_gpgkeys(repofile):
    with open(repofile) as handle:
        content = handle.read()
    for value in GPGKEY_RE.findall(content):
        for url in value.replace(',', ' ').split():
            if url.startswith('file://'):
                path = url[len('file://'):]
                if path.startswith(LEAPP_PREFIX):
                    yield path


def main(buildroot, repofiles):
    missing = []
    checked = 0
    for repofile in repofiles:
        for path in iter_leapp_gpgkeys(repofile):
            checked += 1
            # The repofile names the installed path; the build tree mirrors it
            # under buildroot.
            on_disk = os.path.join(buildroot, path.lstrip('/'))
            if not os.path.isfile(on_disk):
                missing.append((repofile, path))

    for repofile, path in missing:
        print('MISSING  {0}: gpgkey {1} is not installed by this package'.format(repofile, path))
    if missing:
        return 1
    print('OK   {0} leapp-installed gpgkey path(s) in {1} repofile(s)'.format(checked, len(repofiles)))
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: check_gpgkey_paths.py <buildroot> <repofile> [<repofile>...]', file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2:]))
