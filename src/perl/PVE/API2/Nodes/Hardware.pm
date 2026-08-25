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

sub _num {
    my ($v, $default) = @_;
    return $default if !defined($v) || $v eq '';
    return 0 + $v;
}

sub _normalize_guest {
    my ($type, $vmid, $d) = @_;
    return {
        vmid      => int($vmid),
        type      => $type,
        name      => $d->{name} // ($type eq 'lxc' ? "CT$vmid" : "VM $vmid"),
        status    => $d->{status} // 'unknown',
        template  => $d->{template} ? 1 : 0,
        tags      => $d->{tags},
        lock      => $d->{lock},
        pid       => defined($d->{pid}) ? int($d->{pid}) : undef,
        cpu       => _num($d->{cpu}, 0),
        cpus      => _num($d->{cpus}, 0),
        mem       => int(_num($d->{mem}, 0)),
        maxmem    => int(_num($d->{maxmem}, 0)),
        disk      => int(_num($d->{disk}, 0)),
        maxdisk   => int(_num($d->{maxdisk}, 0)),
        uptime    => int(_num($d->{uptime}, 0)),
        netin     => int(_num($d->{netin}, 0)),
        netout    => int(_num($d->{netout}, 0)),
        diskread  => int(_num($d->{diskread}, 0)),
        diskwrite => int(_num($d->{diskwrite}, 0)),
    };
}

sub _read_proc_stat_cpu {
    open(my $fh, '<', '/proc/stat') or return;
    my $line = <$fh>;
    close($fh);
    return unless defined($line) && $line =~ /^cpu\s+/;
    my @p = split(/\s+/, $line);
    shift @p; # cpu
    return unless @p >= 4;
    my @v = map { int($_ || 0) } @p[0 .. 9];
    while (@v < 10) { push @v, 0; }
    my ($user, $nice, $system, $idle, $iowait, $irq, $softirq, $steal) = @v;
    my $idle_all = $idle + $iowait;
    my $total = $user + $nice + $system + $idle_all + $irq + $softirq + $steal;
    return ($idle_all, $total);
}

sub _cpu_utilization_pct {
    my $cache = '/var/cache/pve-hw-dashboard/cpu_stat.json';
    my ($idle2, $total2) = _read_proc_stat_cpu();
    return undef unless defined $idle2;

    my $now = time();
    my ($idle1, $total1, $prev_ts);

    if (-r $cache) {
        if (open(my $fh, '<', $cache)) {
            local $/;
            my $raw = <$fh>;
            close($fh);
            if (defined($raw) && $raw =~ /"idle"\s*:\s*(\d+)/) {
                $idle1 = int($1);
            }
            if (defined($raw) && $raw =~ /"total"\s*:\s*(\d+)/) {
                $total1 = int($1);
            }
            if (defined($raw) && $raw =~ /"ts"\s*:\s*([0-9.]+)/) {
                $prev_ts = 0 + $1;
            }
        }
    }

    eval {
        require File::Path;
        File::Path::make_path('/var/cache/pve-hw-dashboard');
        if (open(my $out, '>', $cache)) {
            print {$out} qq|{"idle":$idle2,"total":$total2,"ts":$now}|;
            close($out);
        }
    };

    return undef unless defined($idle1) && defined($total1) && defined($prev_ts);
    my $dt = $now - $prev_ts;
    return undef if $dt < 0.2 || $dt > 180;
    my $d_total = $total2 - $total1;
    my $d_idle = $idle2 - $idle1;
    return undef if $d_total <= 0;
    my $busy = (1 - ($d_idle / $d_total)) * 100;
    $busy = 0 if $busy < 0;
    $busy = 100 if $busy > 100;
    return sprintf('%.1f', $busy) + 0;
}

sub _node_strip {
    require PVE::ProcFSTools;
    my $meminfo = PVE::ProcFSTools::read_meminfo();
    my $uptime = (PVE::ProcFSTools::read_proc_uptime())[0];
    my @loadavg = PVE::ProcFSTools::read_loadavg();
    my $cpuinfo = PVE::ProcFSTools::read_cpuinfo();
    my $cpu_pct = _cpu_utilization_pct();
    return {
        mem           => int(_num($meminfo->{memused}, 0)),
        maxmem        => int(_num($meminfo->{memtotal}, 0)),
        memavailable  => int(_num($meminfo->{memavailable}, 0)),
        uptime        => int(_num($uptime, 0)),
        loadavg       => [
            _num($loadavg[0], 0),
            _num($loadavg[1], 0),
            _num($loadavg[2], 0),
        ],
        cpu_pct       => $cpu_pct,
        cpus          => int(_num($cpuinfo->{cpus}, 0)),
        cpu_cores     => int(_num($cpuinfo->{cores}, 0)),
    };
}

sub pve_hw_guests_json {
    eval { require PVE::Cluster; PVE::Cluster::cfs_update(); };

    my @guests;

    my $qemu = {};
    eval {
        require PVE::QemuServer;
        $qemu = PVE::QemuServer::vmstatus(undef, 1) || {};
    };
    warn "hwguests qemu: $@\n" if $@;
    foreach my $vmid (keys %$qemu) {
        push @guests, _normalize_guest('qemu', $vmid, $qemu->{$vmid});
    }

    my $lxc = {};
    eval {
        require PVE::LXC;
        $lxc = PVE::LXC::vmstatus() || {};
    };
    warn "hwguests lxc: $@\n" if $@;
    foreach my $vmid (keys %$lxc) {
        push @guests, _normalize_guest('lxc', $vmid, $lxc->{$vmid});
    }

    @guests = sort { $a->{vmid} <=> $b->{vmid} } @guests;

    my $running = scalar grep { ($_->{status} // '') eq 'running' } @guests;
    my $stopped = scalar(@guests) - $running;
    my $vms = scalar grep { $_->{type} eq 'qemu' } @guests;
    my $cts = scalar grep { $_->{type} eq 'lxc' } @guests;

    return {
        meta => {
            name => 'Proxmox Node Hardware API',
            version => $API_VERSION,
            collected_at => time(),
            mode => 'guests',
        },
        node => _node_strip(),
        summary => {
            total   => scalar(@guests),
            running => $running,
            stopped => $stopped,
            vms     => $vms,
            cts     => $cts,
        },
        guests => \@guests,
    };
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
        name => 'hw_guests',
        path => 'hwguests',
        method => 'GET',
        description => "Unified VM/LXC guest list with live CPU/memory/disk stats for the Guests dashboard tab.",
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
            return pve_hw_guests_json();
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
