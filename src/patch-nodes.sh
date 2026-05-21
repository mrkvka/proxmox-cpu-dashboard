#!/bin/bash
# Patch Nodes.pm for extended hwinfo and cpufreq POST endpoint

FILE="/usr/share/perl5/PVE/API2/Nodes.pm"

# 1. Replace thermalstate line to use pve-hwinfo.sh
sed -i 's|\$res->{thermalstate} = `sensors -jA`;|\$res->{thermalstate} = `/usr/local/bin/pve-hwinfo.sh`;|' "$FILE"

# 2. Add cpufreq POST endpoint to PVE::API2::Nodes::Nodeinfo.
# This must be inserted before "package PVE::API2::Nodes;". Adding it to the
# root Nodes package either conflicts with the {node} subclass or is invisible
# to /nodes/{node}/... requests.
cat > /tmp/cpufreq_endpoint.pl << 'PERLCODE'

# CPU Frequency control endpoint
__PACKAGE__->register_method({
    name => 'cpufreq',
    path => 'cpufreq',
    method => 'POST',
    description => "Set CPU frequency governor and max frequency",
    permissions => { check => ['perm', '/nodes/{node}', [ 'Sys.Modify' ]] },
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
    returns => { type => 'null' },
    code => sub {
        my ($param) = @_;
        my @valid_govs = qw(conservative ondemand userspace powersave performance schedutil);
        if (defined($param->{governor})) {
            my $gov = $param->{governor};
            die "invalid governor '$gov'\n" unless grep { $_ eq $gov } @valid_govs;
            system('/usr/local/bin/pve-cpufreq-set.sh', $gov, '') == 0
                or die "failed to set governor\n";
        }
        if (defined($param->{max_freq})) {
            my $freq = int($param->{max_freq});
            die "invalid frequency\n" if $freq < 100000 || $freq > 10000000;
            system('/usr/local/bin/pve-cpufreq-set.sh', '', $freq) == 0
                or die "failed to set max frequency\n";
        }
        return undef;
    },
});

PERLCODE

# Remove a previous cpufreq endpoint block, regardless of whether it was
# inserted into the right package or the old root package.
perl -0pi -e "s/\n\n# CPU Frequency control endpoint\n\n?__PACKAGE__->register_method\(\{\n    name => 'cpufreq',\n.*?\n\}\);//s" "$FILE"

awk '
    BEGIN {
        while ((getline line < "/tmp/cpufreq_endpoint.pl") > 0) {
            endpoint = endpoint line "\n";
        }
    }
    /^package PVE::API2::Nodes;$/ {
        printf "%s", endpoint;
    }
    { print }
' "$FILE" > /tmp/Nodes.pm.cpufreq

cp /tmp/Nodes.pm.cpufreq "$FILE"

rm -f /tmp/cpufreq_endpoint.pl /tmp/Nodes.pm.cpufreq
perl -c "$FILE"

echo "NODES.PM PATCHED WITH CPUFREQ ENDPOINT"
grep -c 'cpufreq' "$FILE"
