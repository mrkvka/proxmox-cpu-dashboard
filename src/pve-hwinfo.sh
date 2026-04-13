#!/bin/bash
SENSORS=$(sensors -jA 2>/dev/null)
GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)
AVAIL_GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors 2>/dev/null)
CUR_FREQ=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null)
MIN_FREQ=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq 2>/dev/null)
MAX_FREQ=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq 2>/dev/null)
CPUINFO_MIN=$(cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq 2>/dev/null)
CPUINFO_MAX=$(cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq 2>/dev/null)
AVAIL_FREQ=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_frequencies 2>/dev/null)
GOVS_JSON=$(echo "$AVAIL_GOV" | tr ' ' '\n' | grep -v '^$' | sed 's/.*/"&"/' | paste -sd,)
FREQS_JSON=$(echo "$AVAIL_FREQ" | tr ' ' '\n' | grep -v '^$' | paste -sd,)
CORE_FREQS=""
for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq; do
  val=$(cat "$f" 2>/dev/null)
  [ -n "$val" ] && CORE_FREQS="${CORE_FREQS}${CORE_FREQS:+,}$val"
done
# Remove outer braces from sensors JSON to embed it
SENSORS_INNER=$(echo "$SENSORS" | sed 's/^{//;s/}$//')
echo "{${SENSORS_INNER:+${SENSORS_INNER},}\"cpufreq\":{\"governor\":\"${GOV}\",\"available_governors\":[${GOVS_JSON}],\"scaling_cur_freq\":${CUR_FREQ:-0},\"scaling_min_freq\":${MIN_FREQ:-0},\"scaling_max_freq\":${MAX_FREQ:-0},\"cpuinfo_min_freq\":${CPUINFO_MIN:-0},\"cpuinfo_max_freq\":${CPUINFO_MAX:-0},\"available_frequencies\":[${FREQS_JSON:-}],\"per_core_freq\":[${CORE_FREQS}]}}"
