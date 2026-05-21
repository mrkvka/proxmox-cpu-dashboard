var PVECPUDash = (function() {
    var styleId = 'pve-cpu-dashboard-style';
    var css = [
        '.pve-cpu-summary-row{padding-bottom:8px!important;}',
        '.pve-cpu-summary-row .right-aligned{float:none!important;display:block!important;margin-left:160px;text-align:left!important;min-height:24px;}',
        '.pve-cpu-summary-row .left-aligned{width:145px;white-space:nowrap;}',
        '.pve-cpu-dashboard-html{display:block;width:100%;max-width:100%;color:inherit;font-size:12px;line-height:1.35;text-align:left;}',
        '.pve-cpu-metric-grid{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-start;gap:6px;margin:0;}',
        '.pve-cpu-metric{display:inline-flex;align-items:baseline;box-sizing:border-box;max-width:100%;min-height:0;border:1px solid rgba(128,128,128,.36);border-left-width:3px;border-radius:4px;background:rgba(128,128,128,.08);padding:4px 7px;overflow:hidden;}',
        '.pve-cpu-metric--ok{border-left-color:#23a55a;}',
        '.pve-cpu-metric--warn{border-left-color:#d97706;}',
        '.pve-cpu-metric--danger{border-left-color:#dc2626;}',
        '.pve-cpu-metric--info{border-left-color:#2f80ed;}',
        '.pve-cpu-metric--muted{border-left-color:#8a94a6;}',
        '.pve-cpu-metric-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0;opacity:.72;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}',
        '.pve-cpu-metric-title:after{content:": ";}',
        '.pve-cpu-metric-value{margin-left:3px;font-size:12px;font-weight:700;color:inherit;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}',
        '.pve-cpu-metric-sub{margin-left:6px;font-size:11px;opacity:.58;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}',
        '.pve-cpu-section-label{margin:7px 0 3px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0;opacity:.62;}',
        '.pve-cpu-chip-row{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-start;gap:5px;margin-top:3px;}',
        '.pve-cpu-chip{display:inline-flex;align-items:baseline;box-sizing:border-box;max-width:100%;border:1px solid rgba(128,128,128,.36);border-radius:4px;background:rgba(128,128,128,.08);padding:3px 7px;color:inherit;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}',
        '.pve-cpu-chip b{margin-left:4px;color:inherit;font-weight:700;}',
        '.pve-cpu-chip--ok{border-left:3px solid #23a55a;}',
        '.pve-cpu-chip--warn{border-left:3px solid #d97706;}',
        '.pve-cpu-chip--danger{border-left:3px solid #dc2626;}',
        '.pve-cpu-chip--info{border-left:3px solid #2f80ed;}',
        '.pve-cpu-empty{display:inline-block;border:1px dashed rgba(128,128,128,.42);border-radius:4px;background:rgba(128,128,128,.06);padding:4px 7px;opacity:.72;}',
        '.pve-cpu-control-panel{margin:4px 10px 8px 10px;padding:8px 10px!important;border:1px solid rgba(128,128,128,.36);border-radius:4px;background:rgba(128,128,128,.08);}',
        '.pve-cpu-control-label{display:block;margin:0 0 3px!important;color:inherit;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0;opacity:.72;}',
        '.pve-cpu-control-row{margin-bottom:7px;}',
        '.pve-cpu-primary-button .x-btn-inner{font-weight:700;}'
    ].join('');

    function ensureStyle() {
        if (!document.getElementById(styleId)) {
            var head = document.head || document.getElementsByTagName('head')[0];
            if (!head) {
                return;
            }
            var style = document.createElement('style');
            style.id = styleId;
            style.type = 'text/css';
            style.appendChild(document.createTextNode(css));
            head.appendChild(style);
        }
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[ch];
        });
    }

    function parseState(value) {
        if (value == null || value === '') {
            return {};
        }
        var data = value;
        if (typeof data !== 'object') {
            data = JSON.parse(String(data).trim());
        }
        if (typeof data === 'string') {
            data = JSON.parse(data.trim());
        }
        return data || {};
    }

    function formatMhz(khz) {
        var n = Number(khz);
        return n > 0 ? Math.round(n / 1000) + ' MHz' : 'N/A';
    }

    function tempTone(value) {
        var n = Number(value);
        if (n >= 80) {
            return 'danger';
        }
        if (n >= 65) {
            return 'warn';
        }
        return 'ok';
    }

    function frequencyState(data) {
        if (data.cpu && data.cpu.frequency) {
            var f = data.cpu.frequency;
            return {
                current_khz: f.current_khz,
                min_khz: f.min_khz,
                max_khz: f.max_khz,
                hw_min_khz: f.hw_min_khz,
                hw_max_khz: f.hw_max_khz,
                governor: f.governor,
                available_governors: f.available_governors || [],
                available_frequencies: f.available_frequencies_khz || [],
                per_core_mhz: f.per_core_mhz || []
            };
        }
        var cf = data.cpufreq || {};
        return {
            current_khz: cf.current_khz || cf.scaling_cur_freq,
            min_khz: cf.min_khz || cf.scaling_min_freq,
            max_khz: cf.max_khz || cf.scaling_max_freq,
            hw_min_khz: cf.hw_min_khz || cf.cpuinfo_min_freq,
            hw_max_khz: cf.hw_max_khz || cf.cpuinfo_max_freq,
            governor: cf.governor,
            available_governors: cf.available_governors || [],
            available_frequencies: cf.available_frequencies || [],
            per_core_mhz: data.per_core_mhz || (cf.per_core_freq || []).map(function(f) {
                return Math.round(Number(f) / 1000);
            })
        };
    }

    function cpuState(data) {
        if (data.cpu) {
            return data.cpu;
        }
        return data.cpus || {};
    }

    function temperatures(data) {
        if (data.sensors && data.sensors.temperatures) {
            return data.sensors.temperatures.map(function(item) {
                return {
                    title: sensorTitle(item.chip, item.label),
                    value: item.value_c,
                    sub: item.chip
                };
            });
        }

        var result = [];
        var skipKeys = ['cpufreq', 'cpus'];
        Object.entries(data).forEach(function(entry) {
            var sensor = entry[0];
            if (skipKeys.indexOf(sensor) >= 0) return;
            var temps = entry[1];
            if (!temps || typeof temps !== 'object') return;
            Object.entries(temps).forEach(function(tEntry) {
                var name = tEntry[0];
                var temp = tEntry[1];
                if (!temp || typeof temp !== 'object') return;
                Object.entries(temp).forEach(function(kEntry) {
                    var key = kEntry[0];
                    var val = kEntry[1];
                    if (key.includes('_input') && typeof val === 'number') {
                        result.push({
                            title: sensorTitle(sensor, name),
                            value: val,
                            sub: sensor
                        });
                    }
                });
            });
        });
        return result;
    }

    function fans(data) {
        if (data.sensors && data.sensors.fans) {
            return data.sensors.fans.map(function(item) {
                return {
                    label: item.label,
                    rpm: item.rpm
                };
            });
        }

        var result = [];
        var skipKeys = ['cpufreq', 'cpus'];
        Object.entries(data).forEach(function(entry) {
            var sensor = entry[0];
            if (skipKeys.indexOf(sensor) >= 0) return;
            var readings = entry[1];
            if (!readings || typeof readings !== 'object') return;
            Object.entries(readings).forEach(function(rEntry) {
                var name = rEntry[0];
                var vals = rEntry[1];
                if (!vals || typeof vals !== 'object') return;
                Object.entries(vals).forEach(function(vEntry) {
                    if (vEntry[0].includes('fan') && vEntry[0].includes('_input')) {
                        result.push({
                            label: name,
                            rpm: vEntry[1]
                        });
                    }
                });
            });
        });
        return result;
    }

    function metric(title, value, sub, tone) {
        return '<div class="pve-cpu-metric pve-cpu-metric--' + escapeHtml(tone || 'muted') + '">' +
            '<div class="pve-cpu-metric-title">' + escapeHtml(title) + '</div>' +
            '<div class="pve-cpu-metric-value">' + escapeHtml(value) + '</div>' +
            (sub ? '<div class="pve-cpu-metric-sub">' + escapeHtml(sub) + '</div>' : '') +
            '</div>';
    }

    function chip(label, value, tone) {
        return '<span class="pve-cpu-chip pve-cpu-chip--' + escapeHtml(tone || 'info') + '">' +
            escapeHtml(label) + '<b>' + escapeHtml(value) + '</b></span>';
    }

    function sensorTitle(sensor, name) {
        var sensorLc = String(sensor || '').toLowerCase();
        var nameStr = String(name || '').replace(/_/g, ' ');
        if (sensorLc.indexOf('k10temp') >= 0 || sensorLc.indexOf('coretemp') >= 0) {
            return /^tctl$/i.test(nameStr) ? 'CPU Tctl' : 'CPU ' + nameStr;
        }
        if (sensorLc.indexOf('nvme') >= 0) {
            return 'NVMe ' + nameStr.replace(/^temp\d+\s*/i, '');
        }
        return nameStr || String(sensor || 'Sensor');
    }

    function empty(message) {
        return '<span class="pve-cpu-empty">' + escapeHtml(message) + '</span>';
    }

    ensureStyle();

    return {
        chip: chip,
        cpuState: cpuState,
        empty: empty,
        fans: fans,
        frequencyState: frequencyState,
        formatMhz: formatMhz,
        metric: metric,
        parseState: parseState,
        sensorTitle: sensorTitle,
        temperatures: temperatures,
        tempTone: tempTone
    };
}());

Ext.define('PVE.node.StatusView', {
    extend: 'Proxmox.panel.StatusView',
    alias: 'widget.pveNodeStatus',

    bodyPadding: '15 5 15 5',

    layout: {
        type: 'table',
        columns: 2,
        tableAttrs: {
            style: {
                width: '100%',
            },
        },
    },

    defaults: {
        xtype: 'pmxInfoWidget',
        padding: '0 10 5 10',
    },

    items: [
        {
            itemId: 'cpu',
            iconCls: 'fa fa-fw pmx-itype-icon-processor pmx-icon',
            title: gettext('CPU usage'),
            valueField: 'cpu',
            maxField: 'cpuinfo',
            renderer: Proxmox.Utils.render_node_cpu_usage,
        },
        {
            itemId: 'wait',
            iconCls: 'fa fa-fw fa-clock-o',
            title: gettext('IO delay'),
            valueField: 'wait',
            rowspan: 2,
        },
        {
            itemId: 'load',
            iconCls: 'fa fa-fw fa-tasks',
            title: gettext('Load average'),
            printBar: false,
            textField: 'loadavg',
        },
        {
            xtype: 'box',
            colspan: 2,
            padding: '0 0 20 0',
        },
        {
            iconCls: 'fa fa-fw pmx-itype-icon-memory pmx-icon',
            itemId: 'memory',
            title: gettext('RAM usage'),
            valueField: 'memory',
            maxField: 'memory',
            renderer: Proxmox.Utils.render_node_size_usage,
        },
        {
            itemId: 'ksm',
            printBar: false,
            title: gettext('KSM sharing'),
            textField: 'ksm',
            renderer: function(record) {
                return Proxmox.Utils.render_size(record.shared);
            },
            padding: '0 10 10 10',
        },
        {
            iconCls: 'fa fa-fw fa-hdd-o',
            itemId: 'rootfs',
            title: '/ ' + gettext('HD space'),
            valueField: 'rootfs',
            maxField: 'rootfs',
            renderer: Proxmox.Utils.render_node_size_usage,
        },
        {
            iconCls: 'fa fa-fw fa-refresh',
            itemId: 'swap',
            printSize: true,
            title: gettext('SWAP usage'),
            valueField: 'swap',
            maxField: 'swap',
            renderer: Proxmox.Utils.render_node_size_usage,
        },
        {
            xtype: 'box',
            colspan: 2,
            padding: '0 0 20 0',
        },
        {
            itemId: 'cpus',
            colspan: 2,
            printBar: false,
            title: gettext('CPU(s)'),
            textField: 'cpuinfo',
            renderer: Proxmox.Utils.render_cpu_model,
            value: '',
        },
        {
            itemId: 'kversion',
            colspan: 2,
            title: gettext('Kernel Version'),
            printBar: false,
            textField: 'kversion',
            value: '',
        },
        {
            itemId: 'version',
            colspan: 2,
            printBar: false,
            title: gettext('PVE Manager Version'),
            textField: 'pveversion',
            value: '',
        },
        {
            itemId: 'thermals',
            colspan: 2,
            printBar: false,
            cls: 'pve-cpu-summary-row',
            title: gettext('Thermals'),
            textField: 'thermalstate',
            renderer: function(value) {
                try {
                    var data = PVECPUDash.parseState(value);
                    var result = PVECPUDash.temperatures(data).map(function(item) {
                        return PVECPUDash.metric(
                            item.title,
                            Number(item.value).toFixed(1) + ' \u00b0C',
                            item.sub,
                            PVECPUDash.tempTone(item.value)
                        );
                    });
                    if (result.length === 0) {
                        return PVECPUDash.empty('No temperature sensors detected');
                    }
                    return '<div class="pve-cpu-dashboard-html"><div class="pve-cpu-metric-grid">' +
                        result.join('') + '</div></div>';
                } catch(e) {
                    return PVECPUDash.empty('Thermal data unavailable');
                }
            }
        },
        {
            xtype: 'box',
            colspan: 2,
            padding: '0 0 10 0',
        },
        {
            itemId: 'cpufreq-info',
            colspan: 2,
            printBar: false,
            cls: 'pve-cpu-summary-row',
            title: 'CPU Frequency',
            textField: 'thermalstate',
            renderer: function(value) {
                try {
                    var data = PVECPUDash.parseState(value);
                    var cf = PVECPUDash.frequencyState(data);
                    if (!cf.governor) return 'N/A';
                    var coreFreqs = cf.per_core_mhz || [];
                    var coreGroups = {};
                    coreFreqs.forEach(function(f) { coreGroups[f] = (coreGroups[f] || 0) + 1; });
                    var coreChips = Object.entries(coreGroups).sort(function(a, b) {
                        return Number(b[0]) - Number(a[0]);
                    }).map(function(e) {
                        return PVECPUDash.chip(e[1] + ' cores', e[0] + ' MHz', 'info');
                    });

                    var cpuMetric = '';
                    var cpus = PVECPUDash.cpuState(data);
                    if (cpus && cpus.total) {
                        var on = cpus.online, tot = cpus.total;
                        cpuMetric = PVECPUDash.metric(
                            'Active CPUs',
                            on + ' / ' + tot,
                            on < tot ? 'reduced core count' : 'all cores online',
                            on < tot ? 'warn' : 'ok'
                        );
                    }

                    return '<div class="pve-cpu-dashboard-html">' +
                        '<div class="pve-cpu-metric-grid">' +
                            PVECPUDash.metric('Governor', cf.governor, 'CPU policy', 'info') +
                            PVECPUDash.metric('Current', PVECPUDash.formatMhz(cf.current_khz), 'live frequency', 'ok') +
                            PVECPUDash.metric(
                                'Allowed range',
                                PVECPUDash.formatMhz(cf.min_khz) + ' - ' + PVECPUDash.formatMhz(cf.max_khz),
                                'configured limits',
                                'muted'
                            ) +
                            PVECPUDash.metric(
                                'Hardware range',
                                PVECPUDash.formatMhz(cf.hw_min_khz) + ' - ' + PVECPUDash.formatMhz(cf.hw_max_khz),
                                'CPU capability',
                                'muted'
                            ) +
                            cpuMetric +
                        '</div>' +
                        (coreChips.length > 0 ? '<div class="pve-cpu-section-label">Per-core groups</div><div class="pve-cpu-chip-row">' + coreChips.join('') + '</div>' : '') +
                        '</div>';
                } catch(e) {
                    return 'N/A';
                }
            }
        },
        {
            xtype: 'container',
            itemId: 'cpufreq-controls',
            colspan: 2,
            cls: 'pve-cpu-control-panel',
            layout: {
                type: 'vbox',
                align: 'stretch'
            },
            items: [
                {
                    xtype: 'container',
                    cls: 'pve-cpu-control-row',
                    layout: {
                        type: 'hbox',
                        align: 'middle'
                    },
                    defaults: {
                        margin: '0 12 0 0'
                    },
                    items: [
                        {
                            xtype: 'container',
                            width: 180,
                            layout: 'vbox',
                            items: [
                                {
                                    xtype: 'label',
                                    text: 'Governor',
                                    cls: 'pve-cpu-control-label'
                                },
                                {
                                    xtype: 'combo',
                                    itemId: 'govCombo',
                                    width: 170,
                                    editable: false,
                                    queryMode: 'local',
                                    displayField: 'text',
                                    valueField: 'value',
                                    forceSelection: true,
                                    store: {
                                        fields: ['value', 'text'],
                                        data: []
                                    }
                                }
                            ]
                        },
                        {
                            xtype: 'container',
                            width: 150,
                            layout: 'vbox',
                            items: [
                                {
                                    xtype: 'label',
                                    text: 'Max Freq (MHz)',
                                    cls: 'pve-cpu-control-label'
                                },
                                {
                                    xtype: 'numberfield',
                                    itemId: 'freqField',
                                    width: 140,
                                    minValue: 400,
                                    maxValue: 5000,
                                    step: 100
                                }
                            ]
                        }
                    ]
                },
                {
                    xtype: 'container',
                    layout: {
                        type: 'hbox',
                        align: 'middle'
                    },
                    defaults: {
                        margin: '0 8 0 0'
                    },
                    items: [
                        {
                            xtype: 'button',
                            itemId: 'applyBtn',
                            text: 'Apply',
                            iconCls: 'fa fa-check',
                            cls: 'pve-cpu-primary-button',
                            minWidth: 92,
                            handler: function(btn) {
                                var panel = btn.up('pveNodeStatus');
                                var gov = panel.down('#govCombo').getValue();
                                var freq = panel.down('#freqField').getValue();
                                var node = panel.pveSelNode.data.node;
                                var params = {};
                                if (gov) params.governor = gov;
                                if (freq) params.max_freq = Math.round(freq * 1000);
                                btn.setDisabled(true);
                                btn.setText('Applying...');

                                Proxmox.Utils.API2Request({
                                    url: '/nodes/' + encodeURIComponent(node) + '/cpufreq',
                                    method: 'POST',
                                    params: params,
                                    success: function() {
                                        btn.setDisabled(false);
                                        btn.setText('Apply');
                                        Ext.Msg.alert(
                                            'Success',
                                            'CPU settings applied!<br>Governor: ' + (gov || 'unchanged') +
                                                '<br>Max Freq: ' + (freq ? freq + ' MHz' : 'unchanged')
                                        );
                                        var store = panel.getStore && panel.getStore();
                                        if (store) {
                                            store.load();
                                        }
                                    },
                                    failure: function(response) {
                                        btn.setDisabled(false);
                                        btn.setText('Apply');
                                        Ext.Msg.alert('Error', response.htmlStatus || response.result || 'CPU settings failed');
                                    }
                                });
                            }
                        },
                        {
                            xtype: 'button',
                            text: 'Presets',
                            iconCls: 'fa fa-sliders',
                            minWidth: 92,
                            menu: [
                                {
                                    text: 'Performance (2900 MHz)',
                                    handler: function() {
                                        var panel = this.up('pveNodeStatus');
                                        panel.down('#govCombo').setValue('performance');
                                        panel.down('#freqField').setValue(2900);
                                    }
                                },
                                {
                                    text: 'Balanced (1700 MHz)',
                                    handler: function() {
                                        var panel = this.up('pveNodeStatus');
                                        panel.down('#govCombo').setValue('conservative');
                                        panel.down('#freqField').setValue(1700);
                                    }
                                },
                                {
                                    text: 'Powersave (1400 MHz)',
                                    handler: function() {
                                        var panel = this.up('pveNodeStatus');
                                        panel.down('#govCombo').setValue('powersave');
                                        panel.down('#freqField').setValue(1400);
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            itemId: 'fans-info',
            colspan: 2,
            printBar: false,
            cls: 'pve-cpu-summary-row',
            title: 'Fans',
            textField: 'thermalstate',
            renderer: function(value) {
                try {
                    var data = PVECPUDash.parseState(value);
                    var fans = PVECPUDash.fans(data).map(function(item) {
                        return PVECPUDash.chip(item.label, item.rpm + ' RPM', 'info');
                    });
                    return fans.length > 0 ?
                        '<div class="pve-cpu-dashboard-html"><div class="pve-cpu-chip-row">' + fans.join('') + '</div></div>' :
                        PVECPUDash.empty('No fan sensors detected');
                } catch(e) {
                    return 'N/A';
                }
            }
        }
    ],

    updateTitle: function() {
        var me = this;
        var uptime = Proxmox.Utils.render_uptime(me.getRecordValue('uptime'));
        me.setTitle(me.pveSelNode.data.node + ' (' + gettext('Uptime') + ': ' + uptime + ')');
    },

    initComponent: function() {
        var me = this;

        var stateProvider = Ext.state.Manager.getProvider();
        var repoLink = stateProvider.encodeHToken({
            view: "server",
            rid: 'node/' + me.pveSelNode.data.node,
            ltab: "tasks",
            nodetab: "aptrepositories",
        });

        me.items.unshift({
            xtype: 'pmxNodeInfoRepoStatus',
            itemId: 'repositoryStatus',
            product: 'Proxmox VE',
            repoLink: '#' + repoLink,
            margin: '0 0 10 0'
        });

        me.callParent();

        // populate governor combo from data
        me.on('afterrender', function() {
            var task = setInterval(function() {
                var rec = me.getStore && me.getStore() && me.getStore().first && me.getStore().first();
                if (!rec) return;
                var val = rec.get('thermalstate');
                if (!val) return;
                clearInterval(task);
                try {
                    var data = PVECPUDash.parseState(val);
                    var cf = PVECPUDash.frequencyState(data);
                    var combo = me.down('#govCombo');
                    var freqField = me.down('#freqField');
                    if (combo && cf.available_governors) {
                        combo.getStore().loadData(cf.available_governors.map(function(gov) {
                            return { value: gov, text: gov };
                        }));
                        combo.setValue(cf.governor);
                    }
                    if (freqField && cf.max_khz) {
                        freqField.setValue(cf.max_khz / 1000);
                    }
                } catch(e) {}
            }, 1000);
        });
    },
});
