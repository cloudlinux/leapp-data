"""The audit that would have found libnsl2 without a wrecked box.

An upstream "Removed" event is wrong for CloudLinux when both hold:
  - the package still exists for the target in an enabled target repository, and
  - some CloudLinux/alt package built for the target requires it.

libnsl2, libwmf-lite and LibRaw each satisfied both and silently erased the
CloudLinux stack. libdb, libdb-utils, enchant and libmemcached-awesome satisfy
both too - libdb took alt-cyrus-sasl-lib with it on a run that otherwise looked
clean. Finding these one wrecked box at a time does not scale.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import removal_audit  # noqa: E402


def test_flags_a_removal_the_target_still_ships_and_needs():
    findings = removal_audit.audit(
        removed=['libnsl2'],
        target_packages={'libnsl2': set(), 'alt-python-internal-libs': {'libnsl2'}},
        suppressed=set(),
    )
    assert [f['package'] for f in findings] == ['libnsl2']
    assert findings[0]['required_by'] == ['alt-python-internal-libs']


def test_a_suppressed_removal_is_not_flagged():
    findings = removal_audit.audit(
        removed=['libnsl2'],
        target_packages={'libnsl2': set(), 'alt-python-internal-libs': {'libnsl2'}},
        suppressed={'libnsl2'},
    )
    assert findings == []


def test_a_removal_with_no_target_build_is_not_flagged():
    """Genuinely gone from the target - removing it is correct."""
    findings = removal_audit.audit(
        removed=['obsolete-thing'],
        target_packages={'something-else': set()},
        suppressed=set(),
    )
    assert findings == []


def test_a_removal_nothing_depends_on_is_not_flagged():
    """Present for the target but unused: upstream's removal is harmless."""
    findings = removal_audit.audit(
        removed=['gtk2'],
        target_packages={'gtk2': set(), 'unrelated': set()},
        suppressed=set(),
    )
    assert findings == []


def test_every_dependent_is_named():
    findings = removal_audit.audit(
        removed=['libdb'],
        target_packages={
            'libdb': set(),
            'alt-cyrus-sasl-lib': {'libdb'},
            'alt-openldap11-servers': {'libdb', 'libdb-utils'},
        },
        suppressed=set(),
    )
    assert findings[0]['required_by'] == ['alt-cyrus-sasl-lib', 'alt-openldap11-servers']


def test_a_dependent_that_is_itself_removed_is_not_breakage():
    """qt5 requiring qt5-qtbase when both go is a consistent cascade, not a bug.

    Over the real data this is the difference between 67 findings and 12: the
    self-referential ones (qt5-* needing qt5-*, libdb-devel needing libdb) are
    upstream removing a whole subsystem coherently. Reporting them buries the
    handful that actually break something that survives.
    """
    findings = removal_audit.audit(
        removed=['qt5-qtbase', 'qt5'],
        target_packages={'qt5-qtbase': set(), 'qt5': {'qt5-qtbase'}},
        suppressed=set(),
    )
    assert findings == []


def test_a_surviving_dependent_is_still_breakage():
    """One survivor among removed dependents is enough to report."""
    findings = removal_audit.audit(
        removed=['libdb', 'libdb-devel'],
        target_packages={
            'libdb': set(),
            'libdb-devel': {'libdb'},
            'alt-cyrus-sasl-lib': {'libdb'},
        },
        suppressed=set(),
    )
    assert [f['package'] for f in findings] == ['libdb']
    assert findings[0]['required_by'] == ['alt-cyrus-sasl-lib']


def test_a_modulestream_scoped_removal_reports_its_scope():
    """Upstream's php removal applies only to streams 8.1 and 8.2.

    Reported without that scope it reads as "php is removed", which is false for
    a box on 8.3 and sent a real review down a blind alley. The scope is the
    finding: whether it matters depends entirely on which stream is installed.
    """
    findings = removal_audit.audit(
        removed={'php': {'8.1', '8.2'}},
        target_packages={'php': set(), 'mod_suphp': {'php'}},
        suppressed=set(),
    )
    assert findings[0]['package'] == 'php'
    assert findings[0]['streams'] == ['8.1', '8.2']


def test_an_unscoped_removal_reports_no_streams():
    findings = removal_audit.audit(
        removed={'libnsl2': None},
        target_packages={'libnsl2': set(), 'alt-python-internal-libs': {'libnsl2'}},
        suppressed=set(),
    )
    assert findings[0]['streams'] is None


def test_a_plain_list_of_names_still_works():
    """Callers that do not care about streams keep working."""
    findings = removal_audit.audit(
        removed=['libnsl2'],
        target_packages={'libnsl2': set(), 'alt-python-internal-libs': {'libnsl2'}},
        suppressed=set(),
    )
    assert findings[0]['streams'] is None


def test_packages_not_installed_are_skipped_when_an_inventory_is_given():
    """Without this the audit invents decisions about packages nobody has.

    LibRaw-devel, libdb-devel and libwmf-devel were all reported as pending
    judgements when none of them was installed, so none could ever have reached
    leapp's removal set.
    """
    target = {'LibRaw-devel': set(), 'LibRaw-static': {'LibRaw-devel'},
              'libnsl2': set(), 'alt-python-internal-libs': {'libnsl2'}}

    findings = removal_audit.audit(
        removed=['LibRaw-devel', 'libnsl2'],
        target_packages=target,
        suppressed=set(),
        installed={'libnsl2', 'alt-python-internal-libs'},
    )
    assert [f['package'] for f in findings] == ['libnsl2']


def test_no_inventory_means_report_everything():
    """The screen is still usable with no box to hand - it just over-reports."""
    findings = removal_audit.audit(
        removed=['LibRaw-devel'],
        target_packages={'LibRaw-devel': set(), 'LibRaw-static': {'LibRaw-devel'}},
        suppressed=set(),
    )
    assert [f['package'] for f in findings] == ['LibRaw-devel']
