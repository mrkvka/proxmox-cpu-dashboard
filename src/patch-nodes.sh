#!/bin/bash
# Patch PVE::API2::Nodes.pm — native hardware API on :8006 (ACL + CSRF).
set -euo pipefail

FILE="/usr/share/perl5/PVE/API2/Nodes.pm"
MARKER="# PVE CPU Dashboard native hardware API"

# thermalstate uses our collector
sed -i 's|\$res->{thermalstate} = `sensors -jA`;|\$res->{thermalstate} = `/usr/local/bin/pve-hwinfo.sh`;|' "$FILE"
sed -i 's|\$res->{thermalstate} = `/usr/local/bin/pve-hwinfo.sh`;|\$res->{thermalstate} = `/usr/local/bin/pve-hwinfo.sh`;|' "$FILE" 2>/dev/null || true

cat > /tmp/pve-hw-endpoints.pl << 'PERLCODE'

# PVE CPU Dashboard native hardware API
sub pve_hw_collect_json {
    my ($mode) = @_;
    $mode //= 'full';
    my @cmd = ('/usr/local/bin/pve-hw-collect.py');
    push @cmd, '--compact' if $mode eq 'compact';
    push @cmd, '--live' if $mode eq 'live';
    my $json = '';
    open(my $fh, '-|', @cmd) or die "failed to run pve-hw-collect.py: $!\n";
    while (my $line = <$fh>) { $json .= $line; }
    close($fh) or die "pve-hw-collect.py failed\n";
    return decode_json($json);
}

sub pve_hw_apply_args {
    my ($param) = @_;
    my @cmd = ('/usr/local/bin/pve-hw-apply.py');
    if (defined($param->{profile}) && $param->{profile} ne '') {
        push @cmd, '--profile', $param->{profile};
    }
    if (defined($param->{governor}) && $param->{governor} ne '') {
        push @cmd, '--governor', $param->{governor};
    }
    if (defined($param->{max_freq})) {
        push @cmd, '--max-freq-khz', int($param->{max_freq});
    }
    if (defined($param->{online_cpus})) {
        push @cmd, '--online-cpus', int($param->{online_cpus});
    }
    my $out = '';
    open(my $fh, '-|', @cmd) or die "failed to run pve-hw-apply.py: $!\n";
    while (my $line = <$fh>) { $out .= $line; }
    close($fh) or die "pve-hw-apply.py failed\n";
    return decode_json($out);
}

__PACKAGE__->register_method({
    name => 'hw',
    path => 'hw',
    method => 'GET',
    description => "Full hardware snapshot (CPU, sensors, power, memory, disks).",
    permissions => { check => ['perm', '/nodes/{node}', ['Sys.Audit']] },
    proxyto => 'node',
    protected => 1,
    parameters => {
        additionalProperties => 0,
        properties => {
            node => get_standard_option('pve-node'),
        },
    },
    returns => { type => 'object' },
    code => sub {
        my ($param) = @_;
        return pve_hw_collect_json('full');
    },
});


__PACKAGE__->register_method({
    name => 'hw_live',
    path => 'hwlive',
    method => 'GET',
    description => "Live hardware snapshot for UI polling (fast, cached static fields).",
    permissions => { check => ['perm', '/nodes/{node}', ['Sys.Audit']] },
    proxyto => 'node',
    protected => 1,
    parameters => {
        additionalProperties => 0,
        properties => {
            node => get_standard_option('pve-node'),
        },
    },
    returns => { type => 'object' },
    code => sub {
        my ($param) = @_;
        return pve_hw_collect_json('live');
    },
});

__PACKAGE__->register_method({
    name => 'hw_cpufreq',
    path => 'hwcpufreq',
    method => 'POST',
    description => "Set CPU governor and/or max frequency (kHz).",
    permissions => { check => ['perm', '/nodes/{node}', ['Sys.Modify']] },
    proxyto => 'node',
    protected => 1,
    parameters => {
        additionalProperties => 0,
        properties => {
            node => get_standard_option('pve-node'),
            governor => { type => 'string', optional => 1 },
            max_freq => { type => 'integer', optional => 1, description => 'Max frequency in kHz.' },
        },
    },
    returns => { type => 'object' },
    code => sub {
        my ($param) = @_;
        return pve_hw_apply_args($param);
    },
});

__PACKAGE__->register_method({
    name => 'hw_cpus',
    path => 'hwcpus',
    method => 'POST',
    description => "Set number of logical CPUs kept online.",
    permissions => { check => ['perm', '/nodes/{node}', ['Sys.Modify']] },
    proxyto => 'node',
    protected => 1,
    parameters => {
        additionalProperties => 0,
        properties => {
            node => get_standard_option('pve-node'),
            online_cpus => { type => 'integer' },
        },
    },
    returns => { type => 'object' },
    code => sub {
        my ($param) = @_;
        return pve_hw_apply_args($param);
    },
});

__PACKAGE__->register_method({
    name => 'hw_apply',
    path => 'hwapply',
    method => 'POST',
    description => "Apply profile or combined CPU settings.",
    permissions => { check => ['perm', '/nodes/{node}', ['Sys.Modify']] },
    proxyto => 'node',
    protected => 1,
    parameters => {
        additionalProperties => 0,
        properties => {
            node => get_standard_option('pve-node'),
            profile => { type => 'string', optional => 1 },
            governor => { type => 'string', optional => 1 },
            max_freq => { type => 'integer', optional => 1 },
            online_cpus => { type => 'integer', optional => 1 },
        },
    },
    returns => { type => 'object' },
    code => sub {
        my ($param) = @_;
        return pve_hw_apply_args($param);
    },
});

# Legacy alias kept for older UI integrations
__PACKAGE__->register_method({
    name => 'cpufreq',
    path => 'cpufreq',
    method => 'POST',
    description => "Set CPU governor and max frequency (legacy path).",
    permissions => { check => ['perm', '/nodes/{node}', ['Sys.Modify']] },
    proxyto => 'node',
    protected => 1,
    parameters => {
        additionalProperties => 0,
        properties => {
            node => get_standard_option('pve-node'),
            governor => { type => 'string', optional => 1 },
            max_freq => { type => 'integer', optional => 1 },
        },
    },
    returns => { type => 'object' },
    code => sub {
        my ($param) = @_;
        return pve_hw_apply_args($param);
    },
});

PERLCODE

# Strip previous dashboard blocks (safe idempotent reinstall)
perl -i -0777 -pe 's/\n# PVE CPU Dashboard native hardware API.*?\n(?=package PVE::API2::Nodes;\n)//s' "$FILE"
perl -i -0777 -pe 's/\n# CPU Frequency control endpoint.*?\n\}\);\n//s' "$FILE"

awk -v marker="$MARKER" '
    BEGIN {
        while ((getline line < "/tmp/pve-hw-endpoints.pl") > 0) {
            block = block line "\n"
        }
    }
    /^package PVE::API2::Nodes;$/ && !done {
        printf "%s", block
        done = 1
    }
    { print }
' "$FILE" > /tmp/Nodes.pm.pvehw

cp /tmp/Nodes.pm.pvehw "$FILE"
rm -f /tmp/pve-hw-endpoints.pl /tmp/Nodes.pm.pvehw

perl -c "$FILE"
echo "Nodes.pm patched: native /nodes/{node}/hw API"
grep -c "path => 'hw'" "$FILE" || true
