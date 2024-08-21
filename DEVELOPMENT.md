# Development guide

This document describes common approaches that can be used to modify this package.

## TODO: vendors.d documentation

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
