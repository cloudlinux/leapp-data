"""
Check that leapp data files satisfy the contracts leapp imposes on them.

Two contracts, and a file is checked against whichever apply to it:

* Every asset leapp reads has to advertise a provided_data_streams major that
  matches the stream leapp consumes, or checkconsumedassets inhibits the upgrade
  with "Detected outdated Leapp data assets". Only the major is compared.
* Repomap files additionally have to satisfy RepoMapData.

The repomap half mirrors RepoMapData.load_from_dict in leapp-repository
(repos/system_upgrade/common/libraries/repomaputils.py). Anything this checker
rejects would make the repositoriesmapping actor inhibit the upgrade with
"The repository mapping file is invalid", which is a much more expensive place
to find out.

The checks are deliberately a copy rather than an import: leapp-data has no
dependency on leapp-repository and is built without it. Keep the two in step -
VERSION_FORMAT and REQUIRED_ENTRY_FIELDS below are the parts that drift.
"""

import argparse
import json
import re

# Must equal RepoMapData.VERSION_FORMAT. leapp compares it with ==, not >=, so a
# file one revision behind is rejected outright rather than read leniently.
VERSION_FORMAT = '1.3.0'

# Must match the major of CONSUMED_DATA_STREAM_ID in leapp-repository
# (repos/system_upgrade/common/libraries/config/__init__.py). Only the major is
# compared, and an asset may advertise several streams, so older ones are kept
# alongside rather than replaced - that keeps the data readable by an older leapp
# that is still installed next to it.
CONSUMED_DATA_STREAM_MAJOR = 4

# Keys RepoMapData.add_repository indexes directly. A missing one is a KeyError
# during the upgrade, not a validation message. 'rhui' is read with .get() and so
# is genuinely optional. 'distro' became required in 1.3.0.
REQUIRED_ENTRY_FIELDS = ('repoid', 'channel', 'repo_type', 'arch', 'major_version', 'distro')

# A template that the build substitutes; it is not a literal value, so files
# carrying it are checked for shape but not for the distro's spelling.
TEMPLATE_PLACEHOLDER = '{distro}'


def _check_data_streams(data, problems):
    streams = data.get('provided_data_streams')
    if streams is None:
        # Predates asset versioning. leapp treats it as outdated, but so does the
        # file's own absence of a claim - flagging it here would be noise for the
        # files that genuinely have no header.
        return
    majors = set()
    for stream in streams:
        if not re.match(r'^\d+\.\d+$', str(stream)):
            problems.append('provided_data_streams contains {!r}, which is not MAJOR.MINOR'.format(stream))
            continue
        majors.add(int(str(stream).split('.', 1)[0]))
    if majors and CONSUMED_DATA_STREAM_MAJOR not in majors:
        problems.append(
            'provided_data_streams {} has no stream with major {}, which leapp consumes'.format(
                streams, CONSUMED_DATA_STREAM_MAJOR
            )
        )


def _check_version_format(data, problems):
    found = data.get('version_format')
    if found != VERSION_FORMAT:
        problems.append(
            'version_format is {!r}, leapp requires exactly {!r}'.format(found, VERSION_FORMAT)
        )


def _check_repositories(data, problems):
    """Return the set of declared pesids, reporting entries leapp could not load."""
    pesids = set()
    for family in data.get('repositories', []):
        pesid = family.get('pesid')
        if not pesid:
            problems.append('a repositories item has no pesid')
            continue
        pesids.add(pesid)
        for index, entry in enumerate(family.get('entries', [])):
            missing = [f for f in REQUIRED_ENTRY_FIELDS if f not in entry]
            if missing:
                problems.append(
                    'pesid {!r} entry {} is missing {}'.format(pesid, index, ', '.join(missing))
                )
    return pesids


def _check_mapping(data, pesids, problems):
    for mapping in data.get('mapping', []):
        for entry in mapping.get('entries', []):
            target = entry.get('target')
            if not isinstance(target, list):
                problems.append('mapping entry {!r} has a non-list target'.format(entry.get('source')))
                continue
            for pesid in [entry.get('source')] + target:
                if pesid not in pesids:
                    problems.append(
                        'mapping refers to pesid {!r}, which no repositories item declares'.format(pesid)
                    )


def _check_distro_consistency(data, expected_distro, problems):
    """Every entry should claim the distro whose file this is.

    leapp matches entries against the source and target distro ids, both of which
    are the /etc/os-release ID of the system being upgraded - so an entry naming
    another distro is simply never selected, silently.
    """
    if not expected_distro:
        return
    found = set()
    for family in data.get('repositories', []):
        for entry in family.get('entries', []):
            if 'distro' in entry:
                found.add(entry['distro'])
    unexpected = {d for d in found if d not in (expected_distro, TEMPLATE_PLACEHOLDER)}
    if unexpected:
        problems.append(
            'entries claim distro {}, expected {!r}'.format(
                ', '.join(repr(d) for d in sorted(unexpected)), expected_distro
            )
        )


def check_file(path, expected_distro=None):
    """Return a list of problems; empty means the file is loadable by leapp."""
    try:
        with open(path) as fp:
            data = json.load(fp)
    except ValueError as err:
        return ['not valid JSON: {}'.format(err)]

    problems = []
    _check_data_streams(data, problems)
    if 'repositories' in data or 'mapping' in data:
        _check_version_format(data, problems)
        pesids = _check_repositories(data, problems)
        _check_mapping(data, pesids, problems)
        _check_distro_consistency(data, expected_distro, problems)
    return problems


def main(args):
    failed = 0
    for path in args.path:
        problems = check_file(path, args.distro)
        if problems:
            failed += 1
            print('FAIL {}'.format(path))
            for problem in problems:
                print('       {}'.format(problem))
        else:
            print('OK   {}'.format(path))
    return failed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', nargs='+')
    parser.add_argument(
        '--distro',
        help="the distro every entry in these files should claim, e.g. 'cloudlinux'",
    )
    exit(main(parser.parse_args()))
