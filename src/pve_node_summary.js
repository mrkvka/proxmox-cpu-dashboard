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
            title: gettext('Thermals'),
            textField: 'thermalstate',
            renderer: function(value) {
                try {
                    var data = (typeof value === 'object') ? value : JSON.parse(value.trim());
                    if (typeof data === 'string') data = JSON.parse(data.trim());
                    var result = [];
                    var skipKeys = ['cpufreq'];
                    Object.entries(data).forEach(function(entry) {
                        var sensor = entry[0];
                        if (skipKeys.indexOf(sensor) >= 0) return;
                        var temps = entry[1];
                        var sensorTemps = [];
                        Object.entries(temps).forEach(function(tEntry) {
                            var name = tEntry[0];
                            var temp = tEntry[1];
                            Object.entries(temp).forEach(function(kEntry) {
                                var key = kEntry[0];
                                var val = kEntry[1];
                                if (key.includes('_input')) {
                                    var color = val > 80 ? 'red' : val > 60 ? 'orange' : '#0a0';
                                    sensorTemps.push(name + ': <span style="color:' + color + ';font-weight:bold">' + val.toFixed(1) + ' \u00b0C</span>');
                                }
                            });
                        });
                        if (sensorTemps.length > 0) {
                            result.push('<b>' + sensor + '</b><br>' + sensorTemps.join(' &nbsp;|&nbsp; '));
                        }
                    });
                    return result.join('<br>');
                } catch(e) {
                    return value || 'N/A';
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
            title: 'CPU Frequency',
            textField: 'thermalstate',
            renderer: function(value) {
                try {
                    var data = (typeof value === 'object') ? value : JSON.parse(value.trim());
                    if (typeof data === 'string') data = JSON.parse(data.trim());
                    var cf = data.cpufreq || {};
                    if (!cf.governor) return 'N/A';
                    var freqMHz = function(khz) { return (khz / 1000).toFixed(0) + ' MHz'; };
                    var coreFreqs = (cf.per_core_freq || []).map(function(f) { return (f/1000).toFixed(0); });
                    var coreGroups = {};
                    coreFreqs.forEach(function(f) { coreGroups[f] = (coreGroups[f] || 0) + 1; });
                    var coreStr = Object.entries(coreGroups).map(function(e) { return e[1] + 'x ' + e[0] + ' MHz'; }).join(', ');

                    return '<b>Governor:</b> <span style="color:#00617f;font-weight:bold">' + cf.governor + '</span>' +
                        ' &nbsp;|&nbsp; <b>Current:</b> ' + freqMHz(cf.scaling_cur_freq) +
                        ' &nbsp;|&nbsp; <b>Range:</b> ' + freqMHz(cf.scaling_min_freq) + ' - ' + freqMHz(cf.scaling_max_freq) +
                        ' &nbsp;|&nbsp; <b>HW Limits:</b> ' + freqMHz(cf.cpuinfo_min_freq) + ' - ' + freqMHz(cf.cpuinfo_max_freq) +
                        '<br><b>Cores:</b> ' + coreStr;
                } catch(e) {
                    return 'N/A';
                }
            }
        },
        {
            xtype: 'container',
            itemId: 'cpufreq-controls',
            colspan: 2,
            padding: '5 10 10 10',
            layout: 'hbox',
            items: [
                {
                    xtype: 'label',
                    text: 'Governor: ',
                    margin: '4 5 0 0',
                    style: 'font-weight:bold'
                },
                {
                    xtype: 'combo',
                    itemId: 'govCombo',
                    width: 140,
                    editable: false,
                    store: [],
                    margin: '0 15 0 0'
                },
                {
                    xtype: 'label',
                    text: 'Max Freq (MHz): ',
                    margin: '4 5 0 0',
                    style: 'font-weight:bold'
                },
                {
                    xtype: 'numberfield',
                    itemId: 'freqField',
                    width: 100,
                    minValue: 400,
                    maxValue: 5000,
                    step: 100,
                    margin: '0 15 0 0'
                },
                {
                    xtype: 'button',
                    itemId: 'applyBtn',
                    text: 'Apply',
                    iconCls: 'fa fa-check',
                    margin: '0 10 0 0',
                    handler: function(btn) {
                        var panel = btn.up('pveNodeStatus');
                        var gov = panel.down('#govCombo').getValue();
                        var freq = panel.down('#freqField').getValue();
                        var node = panel.pveSelNode.data.node;
                        var params = {};
                        if (gov) params.governor = gov;
                        if (freq) params.max_freq = freq * 1000;
                        btn.setDisabled(true);
                        btn.setText('Applying...');
                        var bodyParts = [];
                        if (gov) bodyParts.push('governor=' + encodeURIComponent(gov));
                        if (freq) bodyParts.push('max_freq=' + encodeURIComponent(freq * 1000));
                        var xhr = new XMLHttpRequest();
                        xhr.open('POST', 'http://' + window.location.hostname + ':8087/cpufreq');
                        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                        xhr.onload = function() {
                            btn.setDisabled(false);
                            btn.setText('Apply');
                            if (xhr.status === 200) {
                                Ext.Msg.alert('Success', 'CPU settings applied!<br>Governor: ' + (gov || 'unchanged') + '<br>Max Freq: ' + (freq ? freq + ' MHz' : 'unchanged'));
                            } else {
                                Ext.Msg.alert('Error', 'Failed: ' + xhr.responseText);
                            }
                        };
                        xhr.onerror = function() {
                            btn.setDisabled(false);
                            btn.setText('Apply');
                            Ext.Msg.alert('Error', 'Connection failed. Is pve-cpufreq-api running?');
                        };
                        xhr.send(bodyParts.join('&'));
                    }
                },
                {
                    xtype: 'button',
                    text: 'Presets',
                    iconCls: 'fa fa-sliders',
                    margin: '0 0 0 5',
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
        },
        {
            itemId: 'fans-info',
            colspan: 2,
            printBar: false,
            title: 'Fans',
            textField: 'thermalstate',
            renderer: function(value) {
                try {
                    var data = (typeof value === 'object') ? value : JSON.parse(value.trim());
                    if (typeof data === 'string') data = JSON.parse(data.trim());
                    var fans = [];
                    var skipKeys = ['cpufreq'];
                    Object.entries(data).forEach(function(entry) {
                        var sensor = entry[0];
                        if (skipKeys.indexOf(sensor) >= 0) return;
                        var readings = entry[1];
                        Object.entries(readings).forEach(function(rEntry) {
                            var name = rEntry[0];
                            var vals = rEntry[1];
                            Object.entries(vals).forEach(function(vEntry) {
                                if (vEntry[0].includes('fan') && vEntry[0].includes('_input')) {
                                    fans.push(name + ': ' + vEntry[1] + ' RPM');
                                }
                            });
                        });
                    });
                    return fans.length > 0 ? fans.join(' &nbsp;|&nbsp; ') : '<span style="color:#888">No fan sensors detected</span>';
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
                    var data = (typeof val === 'object') ? val : JSON.parse(val);
                    if (typeof data === 'string') data = JSON.parse(data);
                    var cf = data.cpufreq || {};
                    var combo = me.down('#govCombo');
                    var freqField = me.down('#freqField');
                    if (combo && cf.available_governors) {
                        combo.setStore(cf.available_governors);
                        combo.setValue(cf.governor);
                    }
                    if (freqField && cf.scaling_max_freq) {
                        freqField.setValue(cf.scaling_max_freq / 1000);
                    }
                } catch(e) {}
            }, 1000);
        });
    },
});
