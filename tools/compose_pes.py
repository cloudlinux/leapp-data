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


def compose(upstream_path, overlay_path):
    with open(upstream_path) as fp:
        upstream = json.load(fp)
    with open(overlay_path) as fp:
        overlay = json.load(fp)

    upstream_events = upstream['packageinfo']
    upstream_ids = {event_identity(e) for e in upstream_events}

    adopted = [e for e in overlay['packageinfo'] if event_identity(e) in upstream_ids]
    ours = [e for e in overlay['packageinfo'] if event_identity(e) not in upstream_ids]

    composed = collections.OrderedDict()
    composed['timestamp'] = overlay.get('timestamp') or upstream.get('timestamp')
    composed['provided_data_streams'] = overlay.get('provided_data_streams')
    composed['packageinfo'] = upstream_events + ours
    return composed, adopted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', help='the upstream PES layer')
    parser.add_argument('overlay', help='the CloudLinux PES layer')
    parser.add_argument('output', help='where to write the composed pes-events.json')
    args = parser.parse_args()

    composed, adopted = compose(args.upstream, args.overlay)

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
