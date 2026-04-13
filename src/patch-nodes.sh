#!/bin/bash
# Patch Nodes.pm for extended hwinfo and cpufreq POST endpoint

FILE="/usr/share/perl5/PVE/API2/Nodes.pm"

# 1. Replace thermalstate line to use pve-hwinfo.sh
sed -i 's|\$res->{thermalstate} = `sensors -jA`;|\$res->{thermalstate} = `/usr/local/bin/pve-hwinfo.sh`;|' "$FILE"

# 2. Add cpufreq POST endpoint - insert before the last "1;" in the file
# Find line number of the status method's thermalstate and add the endpoint after the status method
cat >> /tmp/cpufreq_endpoint.pl << 'PERLCODE'

__PACKAGE__->register_method({
    name => 'cpufreq',
    path => '{node}/cpufreq',
    method => 'POST',
    description => "Set CPU frequency governor and max frequency",
    permissions => { check => ['perm', '/nodes/{node}', [ 'Sys.Modify' ]] },
    protected => 1,
    parameters => {
        additionalProperties => 0,
        properties => {
            node => { type => 'string' },
            governor => { type => 'string', optional => 1 },
            max_freq => { type => 'integer', optional => 1 },
        },
    },
    returns => { type => 'null' },
    code => sub {
        my ($param) = @_;
        my @valid_govs = qw(conservative ondemand userspace powersave performance schedutil);
        if (defined($param->{governor})) {
            my $gov = $param->{governor};
            die "invalid governor '$gov'\n" unless grep { $_ eq $gov } @valid_govs;
            system("/usr/local/bin/pve-cpufreq-set.sh '$gov' ''");
        }
        if (defined($param->{max_freq})) {
            my $freq = int($param->{max_freq});
            die "invalid frequency\n" if $freq < 100000 || $freq > 10000000;
            system("/usr/local/bin/pve-cpufreq-set.sh '' '$freq'");
        }
        return undef;
    },
});
PERLCODE

# Insert before the last "1;"
sed -i '/^1;$/i \\n# CPU Frequency control endpoint' "$FILE"
sed -i '/^# CPU Frequency control endpoint$/r /tmp/cpufreq_endpoint.pl' "$FILE"

rm -f /tmp/cpufreq_endpoint.pl

echo "NODES.PM PATCHED WITH CPUFREQ ENDPOINT"
grep -c 'cpufreq' "$FILE"
