/* Proxmox CPU Dashboard v2.2 - inventory: available vs applied */
var PVECPUDash = (function() {
    function ensureStyle() {
        if (document.getElementById('pve-hw-dash-style')) return;
        var css = [
            '.pve-hw-row{padding-bottom:10px!important}',
            '.pve-hw-row .right-aligned{float:none!important;display:block!important;margin-left:155px;text-align:left!important;max-width:calc(100% - 160px)}',
            '.pve-hw-row .left-aligned{width:150px;white-space:nowrap;font-weight:600}',
            '.pve-hw-wrap{font-size:11px;line-height:1.4;color:inherit;max-height:420px;overflow:auto}',
            '.pve-hw-table{width:100%;border-collapse:collapse;margin:0 0 10px 0}',
            '.pve-hw-table th,.pve-hw-table td{border:1px solid rgba(128,128,128,.35);padding:4px 8px;text-align:left;vertical-align:top}',
            '.pve-hw-table th{font-size:10px;text-transform:uppercase;opacity:.75;background:rgba(128,128,128,.12)}',
            '.pve-hw-table td.param{width:28%;font-weight:600}',
            '.pve-hw-table td.avail{width:32%}',
            '.pve-hw-table td.applied{width:32%;font-weight:600}',
            '.pve-hw-table td.src{width:8%;font-size:9px;opacity:.55}',
            '.pve-hw-h3{margin:10px 0 4px;font-size:11px;font-weight:700;text-transform:uppercase;opacity:.8}',
            '.pve-hw-panel{margin:4px 10px 8px;padding:8px 10px!important;border:1px solid rgba(128,128,128,.35);border-radius:4px}',
            '.pve-hw-label{font-size:10px;font-weight:700;text-transform:uppercase;opacity:.7}',
            '.pve-hw-row-warn td.applied{color:#d97706}',
            '.pve-hw-row-danger td.applied{color:#dc2626}'
        ].join('');
        var s = document.createElement('style');
        s.id = 'pve-hw-dash-style';
        s.textContent = css;
        (document.head || document.getElementsByTagName('head')[0]).appendChild(s);
    }

    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, function(c) {
            return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
        });
    }

    function parseState(v) {
        if (!v) return {};
        var d = v;
        if (typeof d !== 'object') d = JSON.parse(String(v).trim());
        if (typeof d === 'string') d = JSON.parse(d.trim());
        return d || {};
    }

    function cellValue(row) {
        return row.applied != null ? row.applied : (row.current != null ? row.current : '');
    }

    function rowClass(param, applied) {
        var p = String(param).toLowerCase();
        var c = String(applied);
        if (p.indexOf('temperature') >= 0 || p.indexOf('temp') >= 0) {
            var n = parseFloat(c);
            if (n >= 80) return 'pve-hw-row-danger';
            if (n >= 65) return 'pve-hw-row-warn';
        }
        if (p.indexOf('wear') >= 0) {
            var w = parseFloat(c);
            if (w >= 80) return 'pve-hw-row-danger';
            if (w >= 50) return 'pve-hw-row-warn';
        }
        if (p.indexOf('online') >= 0 && c.indexOf('/') >= 0) {
            var parts = c.split('/');
            if (parts.length === 2 && parseInt(parts[0], 10) < parseInt(parts[1], 10)) {
                return 'pve-hw-row-warn';
            }
        }
        return '';
    }

    function renderInventory(sections) {
        if (!sections || !sections.length) {
            return '<div class="pve-hw-wrap"><span>—</span></div>';
        }
        var html = ['<div class="pve-hw-wrap">'];
        sections.forEach(function(section) {
            html.push('<div class="pve-hw-h3">' + esc(section.title || section.id) + '</div>');
            html.push('<table class="pve-hw-table"><thead><tr>' +
                '<th>' + gettext('Parameter') + '</th>' +
                '<th>' + gettext('Available') + '</th>' +
                '<th>' + gettext('Applied now') + '</th>' +
                '<th>' + gettext('Source') + '</th>' +
                '</tr></thead><tbody>');
            (section.rows || []).forEach(function(row) {
                var applied = cellValue(row);
                var available = row.available != null ? row.available : '—';
                var cls = rowClass(row.parameter, applied);
                html.push('<tr class="' + cls + '">' +
                    '<td class="param">' + esc(row.parameter) + '</td>' +
                    '<td class="avail">' + esc(available) + '</td>' +
                    '<td class="applied">' + esc(applied) + '</td>' +
                    '<td class="src">' + esc(row.source || '') + '</td>' +
                    '</tr>');
            });
            html.push('</tbody></table>');
        });
        html.push('</div>');
        return html.join('');
    }

    function renderAllInventory(data) {
        if (data.inventory && data.inventory.length) {
            return renderInventory(data.inventory);
        }
        return '<div class="pve-hw-wrap">' + gettext('Loading hardware inventory…') + '</div>';
    }

    function freqOf(data) {
        if (data.cpu && data.cpu.frequency) return data.cpu.frequency;
        var cf = data.cpufreq || {};
        return {
            governor: cf.governor,
            available_governors: cf.available_governors || [],
            max_khz: cf.max_khz || cf.scaling_max_freq,
            current_khz: cf.current_khz || cf.scaling_cur_freq
        };
    }

    function cpuOf(data) {
        return data.cpu || data.cpus || {};
    }

    function repaintInventory(panel, data) {
        panel._pveHwData = data;
        var widget = panel.down('#pveHwInventory');
        if (widget && widget.getEl) {
            var right = widget.getEl().down('.right-aligned');
            if (right) right.setHtml(PVECPUDash.renderAllInventory(data));
        }
    }

    function fetchFull(panel, cb) {
        var node = panel.pveSelNode.data.node;
        Proxmox.Utils.API2Request({
            url: '/nodes/' + encodeURIComponent(node) + '/hw',
            method: 'GET',
            success: function(resp) {
                var data = (resp.result && resp.result.data) ? resp.result.data : (resp.result || {});
                repaintInventory(panel, data);
                if (cb) cb(data);
            },
            failure: function() {
                if (cb) cb(panel._pveHwData || {});
            }
        });
    }

    function applySettings(panel, settings) {
        var node = panel.pveSelNode.data.node;
        var base = '/nodes/' + encodeURIComponent(node);
        var done = function() {
            Ext.Msg.alert(gettext('Success'), gettext('Settings applied'));
            fetchFull(panel, function() {
                var store = panel.getStore && panel.getStore();
                if (store) store.load();
                var inv = panel.down('#pveHwInventory');
                if (inv && inv.update) inv.update(panel._pveHwData);
            });
        };
        var stepCpufreq = function() {
            if (!settings.governor && !settings.max_freq_khz) return done();
            var p = { node: node };
            if (settings.governor) p.governor = settings.governor;
            if (settings.max_freq_khz) p.max_freq = settings.max_freq_khz;
            Proxmox.Utils.API2Request({
                url: base + '/hwcpufreq',
                method: 'POST',
                params: p,
                success: done,
                failure: function(r) {
                    Ext.Msg.alert(gettext('Error'), r.htmlStatus || gettext('Failed'));
                }
            });
        };
        if (settings.online_cpus) {
            Proxmox.Utils.API2Request({
                url: base + '/hwcpus',
                method: 'POST',
                params: { node: node, online_cpus: settings.online_cpus },
                success: stepCpufreq,
                failure: function(r) {
                    Ext.Msg.alert(gettext('Error'), r.htmlStatus || gettext('Failed'));
                }
            });
        } else {
            var cpu = cpuOf(panel._pveHwData || {});
            if (cpu.total && cpu.online < cpu.total) {
                Proxmox.Utils.API2Request({
                    url: base + '/hwcpus',
                    method: 'POST',
                    params: { node: node, online_cpus: cpu.total },
                    success: stepCpufreq,
                    failure: stepCpufreq
                });
            } else {
                stepCpufreq();
            }
        }
    }

    return {
        ensureStyle: ensureStyle,
        parseState: parseState,
        renderAllInventory: renderAllInventory,
        renderInventory: renderInventory,
        fetchFull: fetchFull,
        freqOf: freqOf,
        cpuOf: cpuOf,
        applySettings: applySettings,
        repaintInventory: repaintInventory
    };
})();

Ext.define('PVE.node.StatusView', {
    override: 'PVE.node.StatusView',

    initComponent: function() {
        var me = this;
        PVECPUDash.ensureStyle();
        me.callParent();

        me.insert(3, { xtype: 'box', colspan: 2, padding: '0 0 6 0' });

        me.insert(4, {
            colspan: 2,
            cls: 'pve-hw-row',
            itemId: 'pveHwInventory',
            printBar: false,
            title: gettext('Hardware inventory'),
            textField: 'thermalstate',
            renderer: function(v) {
                try {
                    var data = me._pveHwData || PVECPUDash.parseState(v);
                    return PVECPUDash.renderAllInventory(data);
                } catch (e) {
                    return String(e);
                }
            },
            update: function(data) {
                var el = me.getEl && me.getEl();
                if (!el) return;
                var widget = me.down && me.down('#pveHwInventory');
                if (widget && widget.getEl) {
                    var right = widget.getEl().down('.right-aligned');
                    if (right) right.setHtml(PVECPUDash.renderAllInventory(data || {}));
                }
            }
        });

        me.insert(5, {
            xtype: 'container',
            itemId: 'pve-hw-controls',
            colspan: 2,
            cls: 'pve-hw-panel',
            layout: { type: 'vbox', align: 'stretch' },
            items: [{
                xtype: 'container',
                layout: { type: 'hbox', align: 'middle' },
                defaults: { margin: '0 10 0 0' },
                items: [{
                    xtype: 'label',
                    cls: 'pve-hw-label',
                    text: gettext('Governor')
                }, {
                    xtype: 'combo',
                    itemId: 'govCombo',
                    width: 150,
                    editable: false,
                    forceSelection: true,
                    queryMode: 'local',
                    displayField: 'text',
                    valueField: 'value',
                    store: { fields: ['value', 'text'], data: [] }
                }, {
                    xtype: 'label',
                    cls: 'pve-hw-label',
                    text: gettext('Max MHz')
                }, {
                    xtype: 'numberfield',
                    itemId: 'freqField',
                    width: 100,
                    minValue: 400,
                    maxValue: 6000,
                    step: 100
                }, {
                    xtype: 'label',
                    cls: 'pve-hw-label',
                    text: gettext('Online CPUs')
                }, {
                    xtype: 'numberfield',
                    itemId: 'onlineField',
                    width: 70,
                    minValue: 1,
                    maxValue: 256
                }]
            }, {
                xtype: 'container',
                layout: { type: 'hbox' },
                margin: '8 0 0 0',
                defaults: { margin: '0 8 0 0' },
                items: [{
                    xtype: 'button',
                    text: gettext('Apply'),
                    iconCls: 'fa fa-check',
                    handler: function(btn) {
                        var panel = btn.up('pveNodeStatus');
                        var s = {};
                        var gov = panel.down('#govCombo').getValue();
                        var freq = panel.down('#freqField').getValue();
                        var online = panel.down('#onlineField').getValue();
                        if (gov) s.governor = gov;
                        if (freq) s.max_freq_khz = Math.round(freq * 1000);
                        if (online) s.online_cpus = online;
                        PVECPUDash.applySettings(panel, s);
                    }
                }, {
                    xtype: 'button',
                    text: gettext('Presets'),
                    iconCls: 'fa fa-sliders',
                    menu: ['performance', 'balanced', 'powersave', 'emergency', 'restore'].map(function(name) {
                        return {
                            text: Ext.String.capitalize(name),
                            handler: function() {
                                var panel = this.up('pveNodeStatus');
                                var node = panel.pveSelNode.data.node;
                                Proxmox.Utils.API2Request({
                                    url: '/nodes/' + encodeURIComponent(node) + '/hwapply',
                                    method: 'POST',
                                    params: { node: node, profile: name },
                                    success: function() {
                                        PVECPUDash.fetchFull(panel, function(data) {
                                            var store = panel.getStore && panel.getStore();
                                            if (store) store.load();
                                            PVECPUDash.repaintInventory(panel, data);
                                        });
                                    },
                                    failure: function(r) {
                                        Ext.Msg.alert(gettext('Error'), r.htmlStatus || gettext('Failed'));
                                    }
                                });
                            }
                        };
                    })
                }, {
                    xtype: 'button',
                    text: gettext('Refresh inventory'),
                    iconCls: 'fa fa-refresh',
                    handler: function(btn) {
                        var panel = btn.up('pveNodeStatus');
                        PVECPUDash.fetchFull(panel, function(data) {
                            PVECPUDash.repaintInventory(panel, data);
                            var store = panel.getStore && panel.getStore();
                            if (store) store.load();
                        });
                    }
                }]
            }]
        });

        me.on('afterrender', function() {
            PVECPUDash.fetchFull(me, function(data) {
                var inv = me.down('#pveHwInventory');
                PVECPUDash.repaintInventory(me, data);
                var cf = PVECPUDash.freqOf(data);
                var cpu = PVECPUDash.cpuOf(data);
                var combo = me.down('#govCombo');
                if (combo && cf.available_governors) {
                    combo.getStore().loadData(cf.available_governors.map(function(g) {
                        return { value: g, text: g };
                    }));
                    if (cf.governor) combo.setValue(cf.governor);
                }
                var ff = me.down('#freqField');
                if (ff && cf.max_khz) ff.setValue(Math.round(cf.max_khz / 1000));
                var of = me.down('#onlineField');
                if (of && cpu.online) of.setValue(cpu.online);
            });

            var n = 0;
            var timer = setInterval(function() {
                if (++n > 20) clearInterval(timer);
                var rec = me.getStore && me.getStore().first && me.getStore().first();
                if (!rec) return;
                var val = rec.get('thermalstate');
                if (!val) return;
                clearInterval(timer);
                try {
                    var data = PVECPUDash.parseState(val);
                    me._pveHwData = data;
                    var inv = me.down('#pveHwInventory');
                    if (inv && inv.update && (!data.inventory || !data.inventory.length)) {
                        PVECPUDash.fetchFull(me, function(full) {
                            PVECPUDash.repaintInventory(me, full);
                        });
                    } else if (inv && inv.update) {
                        PVECPUDash.repaintInventory(me, data);
                    }
                } catch (e) { /* ignore */ }
            }, 800);
        });
    }
});
