"""
Compose the shipped pes-events.json from an upstream layer and a CloudLinux layer.

leapp reads exactly one unconditional PES file, /etc/leapp/files/pes-events.json
(vendor *_pes.json files are additional, but only load when that vendor's
repositories are active, so our own events cannot live there). That single file
therefore has to contain both upstream's events and ours.

Keeping them in one *source* file is what made rebasing painful: our events and
upstream's become indistinguishable, and working out which is which means
comparing event content across two 20 MB files. So the source is split in two and
the shipped file is generated:

    files/<distro>/pes-events-upstream.json    verbatim from AlmaLinux, never hand-edited
    files/<distro>/pes-events-cloudlinux.json  ours, small enough to read

Refreshing from upstream becomes "replace the upstream layer and look at its
diff". Answering "what do we add?" becomes "read the CloudLinux layer".

An event in the overlay that upstream has since adopted is an error rather than a
duplicate: identity here deliberately ignores repository, minor version and
architecture, because upstream reshapes those freely and a reshaped event is the
same event. When this fires, drop the event from the overlay - upstream now
covers it.

The overlay can also *suppress* an upstream event, through a "suppress_upstream"
list. Adding a contradicting event does not work: leapp keys its own dedup on
(from_release, in_pkgs) and, when two events tie on to_release, keeps both and
applies them as a union - so a Present next to a Removed is ambiguous rather than
an override. Winning the tie by naming a higher to_release minor is worse, since
the event is then filtered out entirely for anyone targeting a lower minor, and
our upgrade paths offer several.

So suppression removes the upstream event at compose time, which is explicit,
reviewable in one place, and leaves exactly one event in the shipped file. Each
rule carries a reason, and a rule matching nothing is reported - upstream
retiring an event it used to ship must not pass silently.
"""

import argparse
import collections
import json
import sys


def _names(packageset):
    if not packageset:
        return ()
    return tuple(sorted((pkg.get('name') or '') for pkg in (packageset.get('package') or [])))


def _major(release):
    return None if not release else release.get('major_version')


def event_identity(event):
    """What makes two PES events 'the same event' across a rebase.

    Deliberately coarse: action, the major-version transition and the package
    names. Repository names, minor versions and architecture lists change shape
    upstream without the event meaning anything different.
    """
    return (
        event.get('action'),
        _major(event.get('initial_release')),
        _major(event.get('release')),
        _names(event.get('in_packageset')),
        _names(event.get('out_packageset')),
    )


def _suppression_key(rule):
    return (
        rule['action'],
        rule['from_major'],
        rule['to_major'],
        tuple(sorted(rule['in_packages'])),
    )


def _upstream_key(event):
    return (
        event.get('action'),
        _major(event.get('initial_release')),
        _major(event.get('release')),
        _names(event.get('in_packageset')),
    )


def compose(upstream_path, overlay_path):
    with open(upstream_path) as fp:
        upstream = json.load(fp)
    with open(overlay_path) as fp:
        overlay = json.load(fp)

    rules = overlay.get('suppress_upstream') or []
    for rule in rules:
        missing = [f for f in ('action', 'from_major', 'to_major', 'in_packages', 'reason')
                   if not rule.get(f)]
        if missing:
            raise ValueError(
                'suppress_upstream rule {0!r} is missing: {1}'.format(rule, ', '.join(missing))
            )
    wanted = {_suppression_key(r): r for r in rules}

    kept_upstream, suppressed = [], []
    for event in upstream['packageinfo']:
        if _upstream_key(event) in wanted:
            suppressed.append(event)
        else:
            kept_upstream.append(event)

    matched = {_upstream_key(e) for e in suppressed}
    unmatched = [r for k, r in wanted.items() if k not in matched]

    upstream_events = kept_upstream
    upstream_ids = {event_identity(e) for e in upstream_events}

    adopted = [e for e in overlay['packageinfo'] if event_identity(e) in upstream_ids]
    ours = [e for e in overlay['packageinfo'] if event_identity(e) not in upstream_ids]

    composed = collections.OrderedDict()
    composed['timestamp'] = overlay.get('timestamp') or upstream.get('timestamp')
    composed['provided_data_streams'] = overlay.get('provided_data_streams')
    composed['packageinfo'] = upstream_events + ours
    return composed, adopted, suppressed, unmatched


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', help='the upstream PES layer')
    parser.add_argument('overlay', help='the CloudLinux PES layer')
    parser.add_argument('output', help='where to write the composed pes-events.json')
    args = parser.parse_args()

    composed, adopted, suppressed, unmatched = compose(args.upstream, args.overlay)

    for event in suppressed:
        print('suppressed upstream event {0} (action={1}) for {2}'.format(
            event.get('id'), event.get('action'),
            ', '.join(_names(event.get('in_packageset')))))

    if unmatched:
        print(
            'ERROR: {0} suppress_upstream rule(s) in {1} match no upstream event.'.format(
                len(unmatched), args.overlay),
            file=sys.stderr,
        )
        for rule in unmatched:
            print('   action={0} {1} -> {2}: {3}'.format(
                rule['action'], rule['from_major'], rule['to_major'],
                ', '.join(rule['in_packages'])), file=sys.stderr)
        print(
            '\nUpstream no longer ships these, so drop the rule - a suppression that'
            ' matches nothing is indistinguishable from one that is load-bearing.',
            file=sys.stderr,
        )
        return 1

    if adopted:
        print(
            'ERROR: {} event(s) in {} are now also in {}.'.format(
                len(adopted), args.overlay, args.upstream
            ),
            file=sys.stderr,
        )
        for event in adopted[:20]:
            print('   action={} {} -> {}'.format(
                event.get('action'),
                list(_names(event.get('in_packageset')))[:3],
                list(_names(event.get('out_packageset')))[:3]), file=sys.stderr)
        print(
            '\nUpstream now covers these, so remove them from the CloudLinux layer'
            ' rather than shipping both.',
            file=sys.stderr,
        )
        return 1

    with open(args.output, 'w') as fp:
        json.dump(composed, fp, indent=4)
        fp.write('\n')
    print('composed {} events ({} upstream + {} CloudLinux) -> {}'.format(
        len(composed['packageinfo']),
        len(composed['packageinfo']) - len(json.load(open(args.overlay))['packageinfo']),
        len(json.load(open(args.overlay))['packageinfo']),
        args.output))
    return 0


if __name__ == '__main__':
    sys.exit(main())
