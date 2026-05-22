package PVE::API2::Nodes::Hardware;

use strict;
use warnings;

use JSON qw(decode_json);

our $API_VERSION = "0.0.0";
for my $vf ("/usr/share/pve-node-hw-api/VERSION") {
    if (-r $vf) {
        open(my $fh, "<", $vf) or next;
        chomp($API_VERSION = <$fh>);
        close($fh);
        last;
    }
}
use PVE::JSONSchema qw(get_standard_option);

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

sub register_api {
    my $pkg = 'PVE::API2::Nodes::Nodeinfo';

    $pkg->register_method({
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

    $pkg->register_method({
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

    $pkg->register_method({
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

    $pkg->register_method({
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

    $pkg->register_method({
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

    # Legacy alias for older integrations
    $pkg->register_method({
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
}

1;
