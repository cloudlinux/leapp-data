import json
import os
import re
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
SCRIPT = os.path.join(ROOT, 'rebuild_ids.py')
SPEC = os.path.join(ROOT, 'leapp-data.spec')


def _event(event_id):
    return {'id': event_id, 'action': 1,
            'in_packageset': {'set_id': 7, 'package': [{'name': 'p'}]},
            'out_packageset': None}


def _write(path, events):
    with open(path, 'w') as fp:
        json.dump({'packageinfo': events}, fp)


def _tree(tmp_path):
    files = tmp_path / 'files'
    vendors = files / 'vendors.d'
    vendors.mkdir(parents=True)
    _write(str(files / 'pes-events.json'), [_event(5), _event(5)])
    _write(str(files / 'pes-events-upstream.json'), [_event(99)])
    _write(str(vendors / 'foo_pes.json'), [_event(1)])
    return files, vendors


def _run(files, vendors, without_dataclasses=False):
    # sys.modules[name] = None makes "import name" raise ImportError, which is
    # what Python 3.6 - the python3 of the el7 and el8 build roots - does for
    # dataclasses.
    block = "sys.modules['dataclasses'] = None; " if without_dataclasses else ''
    code = ("import sys, runpy; {0}sys.argv = [{1!r}, {2!r}, {3!r}]; "
            "runpy.run_path({1!r}, run_name='__main__')").format(block, SCRIPT, str(files), str(vendors))
    return subprocess.run([sys.executable, '-c', code], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


def _ids(path):
    with open(str(path)) as fp:
        return [e['id'] for e in json.load(fp)['packageinfo']]


def test_runs_on_a_python_without_dataclasses(tmp_path):
    files, vendors = _tree(tmp_path)
    result = _run(files, vendors, without_dataclasses=True)
    assert result.returncode == 0, result.stderr


def test_ids_are_unique_and_sequential_across_the_tree_front_file_first(tmp_path):
    files, vendors = _tree(tmp_path)
    assert _run(files, vendors).returncode == 0
    assert _ids(files / 'pes-events.json') == [1, 2]
    assert _ids(vendors / 'foo_pes.json') == [3]


def test_the_uncomposed_layers_are_left_alone(tmp_path):
    files, vendors = _tree(tmp_path)
    assert _run(files, vendors).returncode == 0
    assert _ids(files / 'pes-events-upstream.json') == [99]


def _build_section(spec_text):
    match = re.search(r'^%build\n(.*?)^%install', spec_text, re.S | re.M)
    assert match, 'no %build section'
    return match.group(1)


def test_every_build_step_can_fail_the_build():
    # rpm runs %build under sh -e, which does not stop at a failing command that is
    # not the last of an && list. `make all && make test` let a failed `make all`
    # skip the tests and exit 0 on el7, shipping an unrenumbered pes-events.json.
    with open(SPEC) as fp:
        build = _build_section(fp.read())
    commands = [line for line in build.splitlines() if not line.lstrip().startswith('#')]
    assert [line for line in commands if '&&' in line or '||' in line] == []
