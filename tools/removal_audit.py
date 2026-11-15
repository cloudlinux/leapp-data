"""Audit upstream PES removals against what the target actually ships and needs.

An upstream "Removed" (action=1) event is wrong for CloudLinux when both hold:

  1. the package still exists for the target major in an enabled target
     repository, and
  2. some CloudLinux or alt-* package built for the target requires it.

Removals satisfying both are silently destructive. leapp turns each into
`job erase pkg X [cleandeps,forcebest]`; with the provider gone the dependent's
target build cannot install; and `allow_erasing` converts that failed update
into an uninstall without reporting a problem. libnsl2 took the entire
CloudLinux stack that way, and libdb took alt-cyrus-sasl-lib on a later run that
otherwise looked clean.

Finding these one wrecked box at a time does not scale, so this makes the rule
mechanical. It is deliberately a *report*, not a gate: whether a given removal
should be suppressed is a judgement (the package may be genuinely unwanted on
the target), and the answer belongs in suppress_upstream with a reason.
"""

import argparse
import json
import sys


def audit(removed, target_packages, suppressed, installed=None):
    """Removals the target still ships and still needs.

    A dependent that is itself removed does not count: upstream retiring a whole
    subsystem coherently (qt5 with qt5-qtbase, libdb-devel with libdb) is
    correct, and over the real 9 -> 10 data counting those is the difference
    between 67 findings and the 12 that actually break something surviving.

    :param removed: {name: set(streams) or None}, or a plain iterable of names.
        A stream set means upstream scoped the removal to those module streams,
        and the finding is conditional on one of them being installed.
    :param target_packages: {name: set(required package names)} for the target
    :param suppressed: names already suppressed in the CloudLinux layer
    :param installed: optional inventory. Given one, packages absent from it are
        skipped - they cannot reach leapp's removal set, so reporting them
        manufactures decisions about packages nobody has.
    :returns: [{'package', 'required_by', 'streams'}], sorted
    """
    if not isinstance(removed, dict):
        removed = dict.fromkeys(removed)
    findings = []
    for name in sorted(removed):
        if name in suppressed or name not in target_packages:
            continue
        if installed is not None and name not in installed:
            continue
        dependents = sorted(
            other for other, requires in target_packages.items()
            if other != name and name in requires and other not in removed
        )
        if dependents:
            streams = removed[name]
            findings.append({
                'package': name,
                'required_by': dependents,
                'streams': sorted(streams) if streams else None,
            })
    return findings


def _suppressed_names(overlay_path):
    with open(overlay_path) as fp:
        overlay = json.load(fp)
    names = set()
    for rule in overlay.get('suppress_upstream') or []:
        names.update(rule.get('in_packages') or [])
    return names


def _removed_names(upstream_path, from_major, to_major):
    """{name: set(streams) or None} for packages upstream removes on the transition.

    A package carrying modulestreams is removed only for those streams. Ignoring
    that reads upstream's php event - scoped to 8.1 and 8.2 - as "php is
    removed", which is false for the 8.3 stream and wasted a review.
    """
    with open(upstream_path) as fp:
        upstream = json.load(fp)
    removed = {}
    for event in upstream['packageinfo']:
        if event.get('action') != 1:
            continue
        initial = event.get('initial_release') or {}
        release = event.get('release') or {}
        if initial.get('major_version') != from_major or release.get('major_version') != to_major:
            continue
        for pkg in (event.get('in_packageset') or {}).get('package', []):
            streams = {ms['stream'] for ms in (pkg.get('modulestreams') or []) if ms}
            previous = removed.get(pkg['name'], set()) if pkg['name'] in removed else None
            if previous is None and pkg['name'] in removed:
                continue  # already unscoped - stays unscoped
            if not streams:
                removed[pkg['name']] = None
            else:
                removed[pkg['name']] = (previous or set()) | streams
    return removed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', help='the upstream PES layer')
    parser.add_argument('overlay', help='the CloudLinux PES layer')
    parser.add_argument('requires_json',
                        help='{name: [requires]} for the target repositories, as built by '
                             'repoquery --qf and collected into JSON')
    parser.add_argument('--from-major', type=int, default=9)
    parser.add_argument('--to-major', type=int, default=10)
    parser.add_argument('--installed', metavar='FILE',
                        help='newline-separated package names installed on a source box. '
                             'Without it the audit reports candidates regardless of whether '
                             'anything has them, which over-reports.')
    args = parser.parse_args()

    with open(args.requires_json) as fp:
        target_packages = {k: set(v) for k, v in json.load(fp).items()}

    installed = None
    if args.installed:
        with open(args.installed) as fp:
            installed = {line.strip() for line in fp if line.strip()}

    findings = audit(
        removed=_removed_names(args.upstream, args.from_major, args.to_major),
        target_packages=target_packages,
        suppressed=_suppressed_names(args.overlay),
        installed=installed,
    )

    if not findings:
        print('OK   no unsuppressed removal is still shipped and required for el{0}'
              .format(args.to_major))
        return 0

    print('{0} removal(s) the el{1} target still ships AND still needs:'
          .format(len(findings), args.to_major))
    for finding in findings:
        scope = ''
        if finding['streams']:
            scope = '  [only streams {0}]'.format(', '.join(finding['streams']))
        print('  {0:26s} required by {1}{2}'.format(
            finding['package'], ', '.join(finding['required_by'][:6]), scope))
    print('\nEach is a candidate for suppress_upstream. Judge them individually -'
          '\na package genuinely unwanted on the target should stay removed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
