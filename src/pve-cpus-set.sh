#!/bin/bash
# pve-cpus-set.sh N — keep N logical CPUs online; offline the rest.
#
# CPU0 is never offlined (kernel constraint). CPUs are offlined from
# highest index downward, which on SMT-enabled CPUs hits sibling threads
# first — the most efficient way to shed load.
#
# Examples:
#   pve-cpus-set.sh 16    # all online
#   pve-cpus-set.sh 8     # disable SMT siblings
#   pve-cpus-set.sh 4     # only 4 logical CPUs (UPS mode)
set -e

TARGET="${1:-}"
if [ -z "$TARGET" ] || ! [[ "$TARGET" =~ ^[0-9]+$ ]]; then
    echo "Usage: $0 <number_of_online_cpus>" >&2
    exit 1
fi

# Count total CPUs
MAX=$(ls -d /sys/devices/system/cpu/cpu[0-9]* 2>/dev/null | wc -l)
[ "$MAX" -eq 0 ] && { echo "No CPUs found" >&2; exit 1; }

if [ "$TARGET" -lt 1 ]; then TARGET=1; fi
if [ "$TARGET" -gt "$MAX" ]; then TARGET="$MAX"; fi

# Walk through cpu1..cpuMAX-1 (cpu0 always stays online)
for i in $(seq 1 $((MAX - 1))); do
    ONLINE_FILE="/sys/devices/system/cpu/cpu${i}/online"
    [ ! -w "$ONLINE_FILE" ] && continue
    if [ "$i" -lt "$TARGET" ]; then
        echo 1 > "$ONLINE_FILE" 2>/dev/null || true
    else
        echo 0 > "$ONLINE_FILE" 2>/dev/null || true
    fi
done

# Report how many are actually online now
ACTUAL=0
for f in /sys/devices/system/cpu/cpu[0-9]*/online; do
    [ "$(cat "$f" 2>/dev/null)" = "1" ] && ACTUAL=$((ACTUAL + 1))
done
# cpu0 has no "online" file on most systems — always counts
HAS_CPU0_FILE=0
[ -f /sys/devices/system/cpu/cpu0/online ] && HAS_CPU0_FILE=1
if [ "$HAS_CPU0_FILE" -eq 0 ]; then ACTUAL=$((ACTUAL + 1)); fi

echo "Online CPUs: $ACTUAL (target $TARGET, total $MAX)"
