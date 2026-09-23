# Development guide

This document describes common approaches that can be used to modify this package.

## TODO: vendors.d documentation

## PES data: two layers, composed at build time

leapp reads exactly one unconditional PES file, `/etc/leapp/files/pes-events.json`.
Vendor `*_pes.json` files are read too, but only when that vendor's repositories
are active on the host, so CloudLinux's own events cannot live there.

That single file used to be a single *source* file as well - AlmaLinux's data with
our events mixed in - and nothing marked which was which. Rebasing therefore meant
comparing event content across two 20 MB files and guessing. Worse, most apparent
differences were not differences at all: upstream reshapes repository names and
minor versions freely, so 1654 of 1874 "our" events in the 2026-09 rebase turned
out to be upstream's own events wearing a different field.

So the source is split and the shipped file is generated:

| file | who owns it |
|---|---|
| `files/cloudlinux/pes-events-upstream.json` | AlmaLinux. Never hand-edited. |
| `files/cloudlinux/pes-events-cloudlinux.json` | Us. Small enough to read. |
| `files/cloudlinux/pes-events.json` | Nobody - built, and gitignored. |

`make all` runs `tools/compose_pes.py`, which concatenates the layers and **fails
if an event in our layer has meanwhile been adopted upstream**, naming the events
to delete. Identity there ignores repository, minor version and architecture,
because an event upstream reshaped is still the same event.

Event ids are assigned by `rebuild_ids.py` over the *built* tree, not the source.
They are an artefact of concatenation order, so committing them made every PES
change churn every other PES file - 42,000 lines of the epel template moved in the
2026-09 rebase for no reason but renumbering.

### Refreshing from upstream

```
git fetch AlmaLinux
python3 tools/refresh_upstream_pes.py AlmaLinux/devel-ng-<version>
make DIST_VERSION=9 all test
```

The script prints the event count per version transition before and after, so a
refresh that quietly drops a transition is visible. Review the diff of the
upstream layer; our layer should not move unless compose tells you an event has
been adopted.

## TODO: files documentation


## Local build

This codebase is shipped within leapp-data rpm package. 
In order to create files structure identical to the rpm 
package already installed on the server, run:
```
make all
```
   
This command creates build directory out of git source
that can be later copied to remote machine as-is.

Build directory can also be installed using following command:
```
make install
```

or
```
make install PREFIX=/installroot
```


## Running tests

This package has some bundled tests located inside the tests directory
which you can run as following:
```
make all
make test
```

Make sure that you run `make all` after making code changes
because currently tests are applied to the build directory.


## Local rpm build

To build rpm locally, you need Centos7 machine and run following commands:
```
sudo yum install -y rpmdevtools rpmlint yum-utils
sudo yum-builddep leapp-data.spec
rpmdev-setuptree

make rpm
```
