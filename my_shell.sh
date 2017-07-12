#!/bin/sh

CURDIR="$1"; shift
TARGET="$1"; shift
CMDLINE="$@"; shift

echo CURDIR: "$CURDIR" >> /home/user/tmp/compile-db.txt
echo TARGET: "$TARGET" >> /home/user/tmp/compile-db.txt
echo CMDLINE: "$CMDLINE" >> /home/user/tmp/compile-db.txt

touch "$TARGET"
