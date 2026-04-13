#!/bin/bash
# Usage: pve-cpufreq-set.sh [governor] [max_freq_khz]
GOVERNOR="$1"
MAX_FREQ="$2"

VALID_GOVS=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors 2>/dev/null)

if [ -n "$GOVERNOR" ]; then
  if echo "$VALID_GOVS" | grep -qw "$GOVERNOR"; then
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
      echo "$GOVERNOR" > "$cpu" 2>/dev/null
    done
    echo "Governor set to $GOVERNOR"
  else
    echo "Invalid governor: $GOVERNOR" >&2
    exit 1
  fi
fi

if [ -n "$MAX_FREQ" ]; then
  if [ "$MAX_FREQ" -gt 0 ] 2>/dev/null; then
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq; do
      echo "$MAX_FREQ" > "$cpu" 2>/dev/null
    done
    echo "Max freq set to $MAX_FREQ"
  else
    echo "Invalid frequency: $MAX_FREQ" >&2
    exit 1
  fi
fi
