/* Guests dashboard tab (Pulse-style). Requires pve_hw_core.js */
Ext.define('PVE.node.GuestsView', {
    extend: 'Ext.panel.Panel',
    alias: 'widget.pveNodeGuests',

    layout: { type: 'vbox', align: 'stretch' },
    border: false,
    bodyPadding: 0,

    initComponent: function() {
        var me = this;
        PVECPUDash.ensureStyle();

        me._guestFilter = { type: 'all', status: 'all', query: '' };
        me._guestPollMs = 3000;

        me.items = [{
            xtype: 'container',
            itemId: 'pveGuestsStrip',
            cls: 'pve-hw-panel pve-guests-strip',
            margin: '8 10 4 10',
            html: '<div class="pve-guests-strip-inner">' + gettext('Loading…') + '</div>'
        }, {
            xtype: 'container',
            itemId: 'pveGuestsFilters',
            cls: 'pve-hw-panel',
            margin: '0 10 4 10',
            layout: { type: 'hbox', align: 'middle' },
            defaults: { margin: '0 8 0 0' },
            items: [{
                xtype: 'textfield',
                itemId: 'guestSearch',
                emptyText: gettext('Search name / ID'),
                width: 180,
                enableKeyEvents: true,
                listeners: {
                    change: function(field) {
                        me._guestFilter.query = String(field.getValue() || '').toLowerCase();
                        me._applyGuestFilter();
                    }
                }
            }, {
                xtype: 'combo',
                itemId: 'guestTypeFilter',
                width: 90,
                editable: false,
                forceSelection: true,
                queryMode: 'local',
                displayField: 'text',
                valueField: 'value',
                value: 'all',
                store: {
                    fields: ['value', 'text'],
                    data: [
                        { value: 'all', text: gettext('All') },
                        { value: 'qemu', text: 'VM' },
                        { value: 'lxc', text: 'LXC' }
                    ]
                },
                listeners: {
                    change: function(field, value) {
                        me._guestFilter.type = value || 'all';
                        me._applyGuestFilter();
                    }
                }
            }, {
                xtype: 'combo',
                itemId: 'guestStatusFilter',
                width: 110,
                editable: false,
                forceSelection: true,
                queryMode: 'local',
                displayField: 'text',
                valueField: 'value',
                value: 'all',
                store: {
                    fields: ['value', 'text'],
                    data: [
                        { value: 'all', text: gettext('All') },
                        { value: 'running', text: gettext('Running') },
                        { value: 'stopped', text: gettext('Stopped') }
                    ]
                },
                listeners: {
                    change: function(field, value) {
                        me._guestFilter.status = value || 'all';
                        me._applyGuestFilter();
                    }
                }
            }, {
                xtype: 'component',
                flex: 1
            }, {
                xtype: 'button',
                text: gettext('Refresh'),
                iconCls: 'fa fa-refresh',
                handler: function() {
                    me._loadGuests(true);
                }
            }]
        }, {
            xtype: 'grid',
            itemId: 'pveGuestsGrid',
            flex: 1,
            border: false,
            cls: 'pve-guests-grid',
            margin: '0 10 8 10',
            store: {
                fields: [
                    'vmid', 'type', 'name', 'status', 'template', 'tags', 'lock',
                    'cpu', 'cpus', 'mem', 'maxmem', 'disk', 'maxdisk',
                    'uptime', 'netin', 'netout', 'diskread', 'diskwrite',
                    'cpu_pct', 'mem_pct', 'disk_pct'
                ],
                data: [],
                sorters: [{ property: 'vmid', direction: 'ASC' }]
            },
            columns: [{
                text: gettext('Name'),
                dataIndex: 'name',
                flex: 1.4,
                minWidth: 140,
                renderer: function(v, meta, rec) {
                    var running = rec.get('status') === 'running';
                    var dot = '<span class="pve-guest-dot ' + (running ? 'ok' : 'off') + '"></span>';
                    return dot + '<span class="pve-guest-name">' + Ext.String.htmlEncode(v || '') + '</span>';
                }
            }, {
                text: gettext('Type'),
                dataIndex: 'type',
                width: 70,
                renderer: function(v) {
                    var cls = v === 'lxc' ? 'lxc' : 'vm';
                    var label = v === 'lxc' ? 'LXC' : 'VM';
                    return '<span class="pve-guest-pill ' + cls + '">' + label + '</span>';
                }
            }, {
                text: 'ID',
                dataIndex: 'vmid',
                width: 60
            }, {
                text: 'CPU',
                dataIndex: 'cpu_pct',
                flex: 1.1,
                minWidth: 130,
                renderer: function(v, meta, rec) {
                    return PVECPUDash.renderUsageBar(v, {
                        label: Math.round(v || 0) + '% (' + (rec.get('cpus') || 0) + ' cores)'
                    });
                }
            }, {
                text: 'MEM',
                dataIndex: 'mem_pct',
                flex: 1.2,
                minWidth: 150,
                renderer: function(v, meta, rec) {
                    return PVECPUDash.renderUsageBar(v, {
                        label: Math.round(v || 0) + '% (' +
                            PVECPUDash.formatBytes(rec.get('mem')) + ' / ' +
                            PVECPUDash.formatBytes(rec.get('maxmem')) + ')'
                    });
                }
            }, {
                text: 'DISK',
                dataIndex: 'disk_pct',
                flex: 1.2,
                minWidth: 150,
                renderer: function(v, meta, rec) {
                    var max = rec.get('maxdisk') || 0;
                    var used = rec.get('disk') || 0;
                    if (!max) {
                        return '<span class="pve-guest-muted">—</span>';
                    }
                    return PVECPUDash.renderUsageBar(v, {
                        label: Math.round(v || 0) + '% (' +
                            PVECPUDash.formatBytes(used) + ' / ' +
                            PVECPUDash.formatBytes(max) + ')'
                    });
                }
            }, {
                text: gettext('Uptime'),
                dataIndex: 'uptime',
                width: 90,
                renderer: function(v, meta, rec) {
                    if (rec.get('status') !== 'running') {
                        return '<span class="pve-guest-muted">—</span>';
                    }
                    return Ext.String.htmlEncode(PVECPUDash.formatUptime(v));
                }
            }, {
                text: 'NET',
                dataIndex: 'netin',
                width: 100,
                renderer: function(v, meta, rec) {
                    return PVECPUDash.renderGuestRate(rec, 'net');
                }
            }, {
                text: 'IO',
                dataIndex: 'diskread',
                width: 100,
                renderer: function(v, meta, rec) {
                    return PVECPUDash.renderGuestRate(rec, 'disk');
                }
            }],
            viewConfig: {
                stripeRows: true,
                emptyText: gettext('No guests match the current filter.'),
                deferEmptyText: false
            },
            listeners: {
                itemdblclick: function(view, rec) {
                    PVECPUDash.openGuest(rec.get('type'), rec.get('vmid'));
                }
            }
        }];

        me.callParent();

        me.on('activate', function() {
            me._loadGuests(true);
            me._startGuestPoll();
        });
        me.on('deactivate', function() {
            me._stopGuestPoll();
        });
        me.on('destroy', function() {
            me._stopGuestPoll();
            me._guestLoaded = false;
        });
    },

    _enrichGuests: function(list) {
        return (list || []).map(function(g) {
            var cpuPct = Math.max(0, Math.min(100, (Number(g.cpu) || 0) * 100));
            var memPct = g.maxmem ? Math.max(0, Math.min(100, (g.mem / g.maxmem) * 100)) : 0;
            var diskPct = g.maxdisk ? Math.max(0, Math.min(100, (g.disk / g.maxdisk) * 100)) : 0;
            return Ext.apply({}, g, {
                cpu_pct: cpuPct,
                mem_pct: memPct,
                disk_pct: diskPct
            });
        });
    },

    _updateStrip: function(data) {
        var strip = this.down('#pveGuestsStrip');
        if (!strip) return;
        var node = (data && data.node) || {};
        var sum = (data && data.summary) || {};
        var memPct = node.maxmem ? Math.round((node.mem / node.maxmem) * 100) : 0;
        var load = (node.loadavg && node.loadavg[0] != null) ? Number(node.loadavg[0]).toFixed(2) : '—';
        var html = [
            '<div class="pve-guests-strip-inner">',
            '<span class="pve-guests-chip"><b>' + Ext.String.htmlEncode(gettext('Guests')) + '</b> ' +
                (sum.running || 0) + '/' + (sum.total || 0) + ' ' + Ext.String.htmlEncode(gettext('running')) + '</span>',
            '<span class="pve-guests-chip">VM ' + (sum.vms || 0) + ' · LXC ' + (sum.cts || 0) + '</span>',
            '<span class="pve-guests-chip">Load ' + Ext.String.htmlEncode(String(load)) +
                (node.cpus ? ' / ' + node.cpus + ' CPU' : '') + '</span>',
            '<span class="pve-guests-chip">RAM ' + memPct + '% (' +
                Ext.String.htmlEncode(PVECPUDash.formatBytes(node.mem || 0)) + ' / ' +
                Ext.String.htmlEncode(PVECPUDash.formatBytes(node.maxmem || 0)) + ')</span>',
            '<span class="pve-guests-chip">' + Ext.String.htmlEncode(gettext('Uptime')) + ' ' +
                Ext.String.htmlEncode(PVECPUDash.formatUptime(node.uptime || 0)) + '</span>',
            '</div>'
        ].join('');
        strip.update(html);
    },

    _applyGuestFilter: function() {
        var me = this;
        var grid = me.down('#pveGuestsGrid');
        if (!grid) return;
        var store = grid.getStore();
        var f = me._guestFilter || {};
        var all = me._guestAll || [];
        var filtered = all.filter(function(g) {
            if (f.type && f.type !== 'all' && g.type !== f.type) return false;
            if (f.status && f.status !== 'all' && g.status !== f.status) return false;
            if (f.query) {
                var q = f.query;
                var hay = String(g.name || '').toLowerCase() + ' ' + String(g.vmid || '');
                if (hay.indexOf(q) < 0) return false;
            }
            return true;
        });
        store.loadData(filtered);
    },

    _loadGuests: function(force) {
        var me = this;
        if (me._guestLoading) return;
        me._guestLoading = true;
        PVECPUDash.fetchGuests(me, function(data) {
            me._guestLoading = false;
            me._guestData = data || {};
            me._guestAll = me._enrichGuests((data && data.guests) || []);
            me._updateStrip(data || {});
            me._applyGuestFilter();
            me._guestLoaded = true;
        }, { force: !!force });
    },

    _startGuestPoll: function() {
        var me = this;
        me._stopGuestPoll();
        me._guestPoll = setInterval(function() {
            if (me.isVisible && me.isVisible()) {
                me._loadGuests(false);
            }
        }, me._guestPollMs || 3000);
    },

    _stopGuestPoll: function() {
        if (this._guestPoll) {
            clearInterval(this._guestPoll);
            this._guestPoll = null;
        }
    }
});
