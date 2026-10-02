"""What the shipped PES data removes on CloudLinux 9 -> 10, composed as the build does.

test_compose_pes.py covers the composition mechanics with synthetic events; this
file pins decisions about the real data, so a suppression dropped by an upstream
refresh or a careless edit shows up here rather than as packages quietly erased
from customer boxes.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import compose_pes  # noqa: E402

_FILES = os.path.join(os.path.dirname(__file__), '..', '..', 'files', 'cloudlinux')

# Removed by upstream on 9 -> 10, absent from AlmaLinux 10, shipped by TuxCare's
# el10-alt-common (and by EPEL 10), and installable against AlmaLinux 10 plus
# alt-common alone (dnf repoclosure, 2026-10-02).
PRESERVED_FROM_ALT_COMMON = [
    'double-conversion', 'double-conversion-devel',
    'enchant-devel',
    'libdb-cxx', 'libdb-cxx-devel', 'libdb-devel-doc', 'libdb-sql', 'libdb-sql-devel',
    'libmemcached-awesome-devel', 'libmemcached-awesome-tools',
    'libwmf',
    'qt5-qtbase', 'qt5-qtbase-common', 'qt5-qtbase-devel', 'qt5-qtbase-examples',
    'qt5-qtbase-gui', 'qt5-qtbase-mysql', 'qt5-qtbase-odbc', 'qt5-qtbase-postgresql',
    'qt5-qtbase-private-devel', 'qt5-qtbase-static',
    'qt5-rpm-macros', 'qt5-srpm-macros',
]

# The CloudLinux and alt-* stack needs these; see each rule's reason.
PRESERVED_FOR_THE_STACK = [
    'LibRaw', 'LibRaw-devel', 'enchant', 'libdb', 'libdb-devel', 'libdb-utils',
    'libmemcached-awesome', 'libnsl2', 'libwmf-devel', 'libwmf-lite',
]

# Also in alt-common, but their el10 builds require 21 qt5 modules nobody ships
# for el10 outside EPEL. Kept, they could not be installed on a box without EPEL.
STILL_REMOVED = ['qt5', 'qt5-devel']


@pytest.fixture(scope='module')
def removed_9_to_10():
    composed, _adopted, _suppressed, unmatched = compose_pes.compose(
        os.path.join(_FILES, 'pes-events-upstream.json'),
        os.path.join(_FILES, 'pes-events-cloudlinux.json'),
    )
    assert unmatched == [], 'a suppression matches no upstream event'
    names = set()
    for event in composed['packageinfo']:
        if event.get('action') != 1:
            continue
        if (event.get('initial_release') or {}).get('major_version') != 9:
            continue
        if (event.get('release') or {}).get('major_version') != 10:
            continue
        names.update(p['name'] for p in (event.get('in_packageset') or {}).get('package', []))
    return names


@pytest.mark.parametrize('name', PRESERVED_FROM_ALT_COMMON + PRESERVED_FOR_THE_STACK)
def test_a_package_cloudlinux_ships_for_el10_is_not_removed(removed_9_to_10, name):
    assert name not in removed_9_to_10


@pytest.mark.parametrize('name', STILL_REMOVED)
def test_a_package_that_cannot_install_on_el10_is_still_removed(removed_9_to_10, name):
    assert name in removed_9_to_10
