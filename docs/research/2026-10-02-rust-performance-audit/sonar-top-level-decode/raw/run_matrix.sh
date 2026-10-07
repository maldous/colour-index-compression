#!/bin/bash
set -u
root=$(cd "$(dirname "$0")" && pwd); out=$(mktemp -d /tmp/cix-top-matrix.XXXXXX); old=/tmp/cix-top-base-target/release; new=/tmp/cix-top-candidate-target/release
printf 'top level decode matrix %.0s' {1..400} > "$out/in"; : > "$root/status.tsv"; : > "$root/commands.log"
for spec in 'g1 --format cixg1 --route raw' 'g2 --format cixg2 --route raw' 'm6 --format cixm6 --fast' 'b1 --external bzip2'; do
 set -- $spec; n=$1; shift; echo "cix $* -f -o ARCHIVE in" >> "$root/commands.log"
 "$old/cix" "$@" -f -o "$out/old-$n" "$out/in" >"$root/$n.old.stdout" 2>"$root/$n.old.stderr"; a=$?
 "$new/cix" "$@" -f -o "$out/new-$n" "$out/in" >"$root/$n.new.stdout" 2>"$root/$n.new.stderr"; b=$?
 cmp "$out/old-$n" "$out/new-$n"; c=$?
 "$old/uncix" -f -o "$out/od-$n" "$out/new-$n" >"$root/$n.olddecode.stdout" 2>"$root/$n.olddecode.stderr"; d=$?
 "$new/uncix" -f -o "$out/nd-$n" "$out/old-$n" >"$root/$n.newdecode.stdout" 2>"$root/$n.newdecode.stderr"; e=$?
 cmp "$out/in" "$out/od-$n"; f=$?; cmp "$out/in" "$out/nd-$n"; g=$?
 cp "$out/new-$n" "$out/trunc-$n"; truncate -s -1 "$out/trunc-$n"; "$new/uncix" -f -o "$out/x-$n" "$out/trunc-$n" >"$root/$n.trunc.stdout" 2>"$root/$n.trunc.stderr"; h=$?
 printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$n" "$a" "$b" "$c" "$d" "$e" "$f/$g" "$h" >> "$root/status.tsv"
done
sha256sum "$out/in" "$old/cix" "$old/uncix" "$new/cix" "$new/uncix" "$out"/new-* > "$root/hashes.sha256"
