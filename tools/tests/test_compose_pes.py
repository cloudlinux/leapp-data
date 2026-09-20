"""Tests for the PES layer composition, including upstream event suppression."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import compose_pes  # noqa: E402


def _event(action, in_names, src=(9, 5), dst=(10, 0), repo='appstream', out_names=()):
    return {
        'id': 1,
        'action': action,
        'in_packageset': {'set_id': 1, 'package': [
            {'name': n, 'repository': repo, 'modulestreams': [None]} for n in in_names]},
        'out_packageset': ({'set_id': 2, 'package': [
            {'name': n, 'repository': repo, 'modulestreams': [None]} for n in out_names]}
            if out_names else None),
        'initial_release': {'major_version': src[0], 'minor_version': src[1], 'os_name': 'AlmaLinux'},
        'release': {'major_version': dst[0], 'minor_version': dst[1], 'os_name': 'AlmaLinux'},
        'architectures': ['x86_64'],
    }


def _write(tmp_path, name, events, extra=None):
    doc = {'timestamp': '2026', 'provided_data_streams': ['4.0'], 'packageinfo': events}
    doc.update(extra or {})
    path = tmp_path / name
    path.write_text(json.dumps(doc))
    return str(path)


def test_suppressed_upstream_event_is_dropped(tmp_path):
    """An upstream REMOVED event we must not ship can be suppressed by name.

    CLOS-7051: AlmaLinux removes libnsl2, libwmf-lite and LibRaw on 9 -> 10,
    which is right for a stock AlmaLinux box. On CloudLinux all three exist for
    el10 and the CloudLinux stack links against them, so shipping the removal
    erases lve-utils, cagefs and lvemanager along with them.
    """
    upstream = _write(tmp_path, 'up.json', [
        _event(1, ['libnsl2']),
        _event(1, ['some-other-pkg']),
    ])
    overlay = _write(tmp_path, 'ours.json', [], extra={
        'suppress_upstream': [
            {'action': 1, 'from_major': 9, 'to_major': 10, 'in_packages': ['libnsl2'],
             'reason': 'CloudLinux el10 alt-python-internal-libs needs libnsl.so.3'},
        ]})

    composed, adopted, suppressed, unmatched = compose_pes.compose(upstream, overlay)

    names = [p['name'] for e in composed['packageinfo']
             for p in (e.get('in_packageset') or {}).get('package', [])]
    assert 'libnsl2' not in names
    assert 'some-other-pkg' in names
    assert len(suppressed) == 1
    assert unmatched == []


def test_a_suppression_that_matches_nothing_is_reported(tmp_path):
    """Upstream dropping the event itself must not pass silently.

    A suppression that no longer matches is either a typo or an event upstream
    has retired. Both need a human: left unreported, the file accumulates rules
    nobody can tell apart from load-bearing ones.
    """
    upstream = _write(tmp_path, 'up.json', [_event(1, ['libnsl2'])])
    overlay = _write(tmp_path, 'ours.json', [], extra={
        'suppress_upstream': [
            {'action': 1, 'from_major': 9, 'to_major': 10, 'in_packages': ['gone-upstream'],
             'reason': 'stale'},
        ]})

    dummy, dummy2, suppressed, unmatched = compose_pes.compose(upstream, overlay)

    assert suppressed == []
    assert len(unmatched) == 1
    assert unmatched[0]['in_packages'] == ['gone-upstream']


def test_suppression_is_scoped_to_the_named_transition(tmp_path):
    """The same package removed on a different transition must be left alone."""
    upstream = _write(tmp_path, 'up.json', [
        _event(1, ['libnsl2'], src=(8, 10), dst=(9, 0)),
        _event(1, ['libnsl2'], src=(9, 5), dst=(10, 0)),
    ])
    overlay = _write(tmp_path, 'ours.json', [], extra={
        'suppress_upstream': [
            {'action': 1, 'from_major': 9, 'to_major': 10, 'in_packages': ['libnsl2'],
             'reason': 'only the 9 to 10 removal is wrong for us'},
        ]})

    composed, dummy, suppressed, dummy2 = compose_pes.compose(upstream, overlay)

    remaining = [(e['initial_release']['major_version'], e['release']['major_version'])
                 for e in composed['packageinfo']]
    assert remaining == [(8, 9)]
    assert len(suppressed) == 1


def test_suppression_requires_a_reason(tmp_path):
    """Every rule states why, or the next rebase cannot judge whether it still holds."""
    upstream = _write(tmp_path, 'up.json', [_event(1, ['libnsl2'])])
    overlay = _write(tmp_path, 'ours.json', [], extra={
        'suppress_upstream': [
            {'action': 1, 'from_major': 9, 'to_major': 10, 'in_packages': ['libnsl2']},
        ]})

    with pytest.raises(ValueError) as exc:
        compose_pes.compose(upstream, overlay)
    assert 'reason' in str(exc.value)


def test_composition_without_suppressions_is_unchanged(tmp_path):
    upstream = _write(tmp_path, 'up.json', [_event(1, ['a'])])
    overlay = _write(tmp_path, 'ours.json', [_event(0, ['b'])])

    composed, adopted, suppressed, unmatched = compose_pes.compose(upstream, overlay)

    assert len(composed['packageinfo']) == 2
    assert (adopted, suppressed, unmatched) == ([], [], [])
