#!/usr/bin/env bash

{ # this ensures the entire script is downloaded #

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Name: install.sh - part of the BeakerLib project
#   Description: Bash helper which allows installing beakerlib's shell
#       scripts directly from GitHub! WARNING: this script only installs
#       .sh files under `/usr/share/beakerlib`. It doesn't install
#       exacutables under `/usr/bin`.
#
#               Author: Alexander Todorov <atodorov@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2017 Red Hat, Inc. All rights reserved.
#
#   This copyrighted material is made available to anyone wishing
#   to use, modify, copy, or redistribute it subject to the terms
#   and conditions of the GNU General Public License version 2.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE. See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public
#   License along with this program; if not, write to the Free
#   Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
#   Boston, MA 02110-1301, USA.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



FILES="journal.sh\
    logging.sh\
    testing.sh\
    rpms.sh\
    infrastructure.sh\
    performance.sh\
    analyze.sh\
    libraries.sh\
    storage.sh \
    synchronisation.sh\
    virtualX.sh\
    beakerlib.sh"


DESTDIR="$1/usr/share/beakerlib"

do_install() {
    F=$1
    # if file not present locally on disk then we must be installing from web
    if [ ! -f $F ]; then
        curl -k -o $DESTDIR/$F "https://raw.githubusercontent.com/beakerlib/beakerlib/master/src/$F"
        chmod 0644 $DESTDIR/$F
    else
        # otherwise we're building an RPM or installing via make
        install -p -m 644 $F $DESTDIR
    fi
}


mkdir -p $DESTDIR
for F in $FILES; do
    do_install $F
done

} # this ensures the entire script is downloaded #
