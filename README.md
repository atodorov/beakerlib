## Installation

To install the library to the root directory, use:

```
$ make
$ make install
```

If you need to install to a different directory, use
```
$ make
$ make DD=/path/to/directory install
```
Running against non-installed tree (except for the in-tree testsuite) is not supported.


To install directly from GitHub use:

```
$ curl -o- https://raw.githubusercontent.com/beakerlib/beakerlib/master/install.sh | bash
```

or:

```
$ wget -qO- https://raw.githubusercontent.com/beakerlib/beakerlib/master/install.sh | bash
```

**NOTE:** web install will not install scripts under `/usr/bin`! It will only
install the `.sh` files of this library!
