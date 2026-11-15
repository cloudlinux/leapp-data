"""
Replace the upstream PES layer with AlmaLinux's current data.

Rebasing PES data used to mean diffing two 20 MB files to work out which events
were ours. With the layers split (see DEVELOPMENT.md) it is this script plus a
look at one diff.

    python3 tools/refresh_upstream_pes.py AlmaLinux/devel-ng-0.25.0

Afterwards, `make DIST_VERSION=9 all` composes the two layers and fails if any
event in the CloudLinux layer has meanwhile been adopted upstream, naming the
events to delete from it.
"""

import argparse
import collections
import json
import subprocess
import sys

UPSTREAM_PATH_IN_THEIR_TREE = 'files/almalinux/pes-events.json'
OUR_UPSTREAM_LAYER = 'files/cloudlinux/pes-events-upstream.json'


def transitions(events):
    counts = collections.Counter()
    for event in events:
        source = (event.get('initial_release') or {}).get('major_version')
        target = (event.get('release') or {}).get('major_version')
        counts[(source, target)] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ref', help='git ref in the AlmaLinux remote, e.g. AlmaLinux/devel-ng-0.25.0')
    parser.add_argument('--path', default=UPSTREAM_PATH_IN_THEIR_TREE,
                        help='path to their pes-events.json within that ref')
    parser.add_argument('--output', default=OUR_UPSTREAM_LAYER)
    args = parser.parse_args()

    try:
        raw = subprocess.check_output(['git', 'show', '{}:{}'.format(args.ref, args.path)])
    except subprocess.CalledProcessError:
        print('Could not read {}:{} - is the AlmaLinux remote fetched?'.format(args.ref, args.path),
              file=sys.stderr)
        return 1

    theirs = json.loads(raw.decode('utf-8'))

    try:
        with open(args.output) as fp:
            before = transitions(json.load(fp)['packageinfo'])
    except (IOError, OSError):
        before = collections.Counter()

    layer = collections.OrderedDict()
    layer['timestamp'] = theirs.get('timestamp')
    layer['provided_data_streams'] = theirs.get('provided_data_streams')
    layer['_source'] = '{} {}'.format(args.ref, args.path)
    layer['packageinfo'] = theirs['packageinfo']
    with open(args.output, 'w') as fp:
        json.dump(layer, fp, indent=4)
        fp.write('\n')

    after = transitions(layer['packageinfo'])
    print('wrote {} ({} events) from {}'.format(args.output, len(layer['packageinfo']), args.ref))
    print('events by transition (was -> now):')
    for transition in sorted(set(before) | set(after), key=str):
        old, new = before.get(transition, 0), after.get(transition, 0)
        flag = '' if old == new else '   <-- changed'
        print('   {} -> {}: {} -> {}{}'.format(transition[0], transition[1], old, new, flag))
    return 0


if __name__ == '__main__':
    sys.exit(main())
