#!/bin/bash
set -eu
work=/tmp/cix-candidate-context-run
mkdir -p "$work"
printf 'CIX candidate context parity fixture\n' > "$work/input"
while [ "$(wc -c < "$work/input")" -lt 512 ]; do
    cat "$work/input" "$work/input" > "$work/input.next"
    mv "$work/input.next" "$work/input"
done
head -c 512 "$work/input" > "$work/input.512"
printf 'RLE-representation-fixture:' > "$work/repetitive"
while [ "$(wc -c < "$work/repetitive")" -lt 768 ]; do
    cat "$work/repetitive" "$work/repetitive" > "$work/repetitive.next"
    mv "$work/repetitive.next" "$work/repetitive"
done
head -c 768 "$work/repetitive" > "$work/repetitive.768"
printf '0123456789abcdef0123456789abcdef\n' > "$work/periodic"
while [ "$(wc -c < "$work/periodic")" -lt 768 ]; do
    cat "$work/periodic" "$work/periodic" > "$work/periodic.next"
    mv "$work/periodic.next" "$work/periodic"
done
head -c 768 "$work/periodic" > "$work/periodic.768"
path=$(awk -F: '$1 == "0" { print $3 }' /proc/self/cgroup)
cg=/sys/fs/cgroup$path
printf 'cgroup_path=%s\n' "$path"
printf 'memory.max=%s\n' "$(cat "$cg/memory.max")"
printf 'memory.swap.max=%s\n' "$(cat "$cg/memory.swap.max")"
printf 'cpuset.cpus.effective=%s\n' "$(cat "$cg/cpuset.cpus.effective")"
printf 'RUSTC=%s\nRUSTDOC=%s\nCARGO=%s\n' \
    /home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc \
    /home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustdoc \
    /home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo
child_cgroup() {
    awk -F: '$1 == "0" { print $3 }' /proc/self/cgroup
}

run_pair() {
    fixture=$1
    format=$2
    effort=$3
    threads=$4
    route=$5
    name="$fixture-$format-$effort-t$threads-${route:-auto}"
    input="$work/$fixture"
    flags="--format $format --block-size 256 --threads $threads --explain"
    if [ "$threads" -gt 1 ]; then flags="$flags --parallelism candidates"; fi
    case "$effort" in
        fast) flags="$flags --fast" ;;
        best) flags="$flags --best" ;;
    esac
    if [ -n "$route" ]; then flags="$flags --route $route"; fi
    printf 'service_shell_cgroup=%s case=%s encoder=base,candidate\n' "$(child_cgroup)" "$name"
    /tmp/cix-base-bin/cix $flags -c "$input" > "$work/base-$name.cix" 2> "$work/base-$name.explain"
    /tmp/cix-candidate-bin/cix $flags -c "$input" > "$work/candidate-$name.cix" 2> "$work/candidate-$name.explain"
    cmp "$work/base-$name.cix" "$work/candidate-$name.cix"
    sed -E -e 's/[0-9]+\.[0-9]+s/<seconds>/g' -e 's/(analyse_seconds|candidate_seconds|search_seconds)=[0-9.]+/\1=<seconds>/g' "$work/base-$name.explain" > "$work/base-$name.explain.normalized"
    sed -E -e 's/[0-9]+\.[0-9]+s/<seconds>/g' -e 's/(analyse_seconds|candidate_seconds|search_seconds)=[0-9.]+/\1=<seconds>/g' "$work/candidate-$name.explain" > "$work/candidate-$name.explain.normalized"
    cmp "$work/base-$name.explain.normalized" "$work/candidate-$name.explain.normalized"
    printf 'service_shell_cgroup=%s case=%s decoder=candidate\n' "$(child_cgroup)" "$name"
    /tmp/cix-candidate-bin/uncix -c < "$work/base-$name.cix" > "$work/restored-candidate-$name"
    printf 'service_shell_cgroup=%s case=%s decoder=base\n' "$(child_cgroup)" "$name"
    /tmp/cix-base-bin/uncix -c < "$work/candidate-$name.cix" > "$work/restored-base-$name"
    cmp "$input" "$work/restored-candidate-$name"
    cmp "$input" "$work/restored-base-$name"
    sha256sum "$work/base-$name.cix" "$work/candidate-$name.cix"
}

for format in cixg1 cixg2; do
    for effort in fast default best; do
        run_pair input.512 "$format" "$effort" 1 ''
    done
done
for fixture in repetitive.768 periodic.768; do
    for threads in 1 2 4; do
        run_pair "$fixture" cixg1 default "$threads" ''
        run_pair "$fixture" cixg2 best "$threads" ''
    done
done
run_pair repetitive.768 cixg1 default 1 composition
run_pair periodic.768 cixg1 default 1 predictor
run_pair periodic.768 cixg2 best 1 ppm
printf bad > "$work/bad.cix"
if /tmp/cix-candidate-bin/uncix -c < "$work/bad.cix" > "$work/bad.out" 2> "$work/bad.err"; then exit 91; fi
if /tmp/cix-base-bin/uncix -c < "$work/bad.cix" > "$work/bad-base.out" 2> "$work/bad-base.err"; then exit 92; fi
printf 'three_byte_bad_magic=both-rejected\n'
