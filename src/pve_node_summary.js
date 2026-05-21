/* Proxmox CPU Dashboard v2 — native PVE API (:8006, ACL + CSRF). */
var PVECPUDash = (function() {
    function ensureStyle() {
        if (document.getElementById('pve-hw-dash-style')) return;
        var css = '.pve-hw-row{padding-bottom:8px!important}.pve-hw-row .right-aligned{float:none!important;display:block!important;margin-left:160px;text-align:left!important}.pve-hw-row .left-aligned{width:145px}.pve-hw-html{font-size:12px;line-height:1.35}.pve-hw-metric{display:inline-flex;border:1px solid rgba(128,128,128,.35);border-left:3px solid #2f80ed;border-radius:4px;padding:4px 7px;margin:0 6px 6px 0}.pve-hw-metric--ok{border-left-color:#23a55a}.pve-hw-metric--warn{border-left-color:#d97706}.pve-hw-metric--danger{border-left-color:#dc2626}.pve-hw-chip{display:inline-block;border:1px solid rgba(128,128,128,.35);border-radius:4px;padding:3px 7px;margin:0 5px 5px 0;font-size:11px}.pve-hw-panel{margin:4px 10px 8px;padding:8px 10px!important;border:1px solid rgba(128,128,128,.35);border-radius:4px}.pve-hw-label{font-size:10px;font-weight:700;text-transform:uppercase;opacity:.7}';
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
        if (typeof d !== 'object') d = JSON.parse(String(d).trim());
        if (typeof d === 'string') d = JSON.parse(d.trim());
        return d || {};
    }

    function freqOf(data) {
        if (data.cpu && data.cpu.frequency) return data.cpu.frequency;
        var cf = data.cpufreq || {};
        return {
            governor: cf.governor,
            available_governors: cf.available_governors || [],
            current_khz: cf.current_khz || cf.scaling_cur_freq,
            max_khz: cf.max_khz || cf.scaling_max_freq,
            hw_min_khz: cf.hw_min_khz || cf.cpuinfo_min_freq,
            hw_max_khz: cf.hw_max_khz || cf.cpuinfo_max_freq,
            per_core_mhz: (cf.per_core_freq || []).map(function(f) { return Math.round(f / 1000); })
        };
    }

    function cpuOf(data) {
        return data.cpu || data.cpus || {};
    }

    function metric(title, value, tone) {
        return '<span class="pve-hw-metric pve-hw-metric--' + (tone || 'ok') + '"><b>' + esc(title) + ':</b> ' + esc(value) + '</span>';
    }

    function renderTemps(data) {
        var temps = (data.sensors && data.sensors.temperatures) ||
            (data.sensors && data.sensors.normalized && data.sensors.normalized.temperatures) || [];
        if (!temps.length) return '<span class="pve-hw-chip">No sensors</span>';
        return '<div class="pve-hw-html">' + temps.map(function(t) {
            var c = t.value_c != null ? t.value_c : t.value;
            var tone = c >= 80 ? 'danger' : (c >= 65 ? 'warn' : 'ok');
            return metric(t.label || t.chip, c + ' °C', tone);
        }).join('') + '</div>';
    }

    function renderFans(data) {
        var fans = (data.sensors && data.sensors.fans) ||
            (data.sensors && data.sensors.normalized && data.sensors.normalized.fans) || [];
        if (!fans.length) return '<span class="pve-hw-chip">No fans</span>';
        return fans.map(function(f) {
            return '<span class="pve-hw-chip">' + esc(f.label) + ': <b>' + esc(f.rpm) + ' RPM</b></span>';
        }).join(' ');
    }

    function renderCpu(data) {
        var cf = freqOf(data);
        var cpu = cpuOf(data);
        var html = [
            metric('Governor', cf.governor || 'n/a', 'ok'),
            metric('Current', Math.round((cf.current_khz || 0) / 1000) + ' MHz', 'ok'),
            metric('Max', Math.round((cf.max_khz || 0) / 1000) + ' MHz', 'ok')
        ];
        if (cpu.total) {
            html.push(metric('Online CPUs', cpu.online + ' / ' + cpu.total, cpu.online < cpu.total ? 'warn' : 'ok'));
        }
        if (data.power && data.power.package_watts != null) {
            html.push(metric('Power', data.power.package_watts + ' W', 'ok'));
        }
        if (cf.per_core_mhz && cf.per_core_mhz.length) {
            html.push(cf.per_core_mhz.map(function(m, i) {
                return '<span class="pve-hw-chip">C' + i + ': ' + m + ' MHz</span>';
            }).join(''));
        }
        return '<div class="pve-hw-html">' + html.join('') + '</div>';
    }

    function apiPost(url, params, ok, fail) {
        Proxmox.Utils.API2Request({
            url: url,
            method: 'POST',
            params: params,
            success: ok,
            failure: fail || function(r) {
                Ext.Msg.alert(gettext('Error'), r.htmlStatus || gettext('Request failed'));
            }
        });
    }

    function applySettings(panel, settings) {
        var node = panel.pveSelNode.data.node;
        var base = '/nodes/' + encodeURIComponent(node);
        var done = function() {
            Ext.Msg.alert(gettext('Success'), gettext('Settings applied'));
            var store = panel.getStore && panel.getStore();
            if (store) store.load();
        };
        var stepCpufreq = function() {
            if (!settings.governor && !settings.max_freq_khz) return done();
            var p = { node: node };
            if (settings.governor) p.governor = settings.governor;
            if (settings.max_freq_khz) p.max_freq = settings.max_freq_khz;
            apiPost(base + '/hwcpufreq', p, done);
        };
        if (settings.online_cpus) {
            apiPost(base + '/hwcpus', { node: node, online_cpus: settings.online_cpus }, stepCpufreq);
        } else {
            var cpu = cpuOf(parseState(panel._pveHwData || {}));
            if (cpu.total && cpu.online < cpu.total) {
                apiPost(base + '/hwcpus', { node: node, online_cpus: cpu.total }, stepCpufreq);
            } else {
                stepCpufreq();
            }
        }
    }

    return {
        ensureStyle: ensureStyle,
        parseState: parseState,
        freqOf: freqOf,
        cpuOf: cpuOf,
        renderTemps: renderTemps,
        renderFans: renderFans,
        renderCpu: renderCpu,
        applySettings: applySettings
    };
})();

Ext.define('PVE.node.StatusView', {
    override: 'PVE.node.StatusView',

    initComponent: function() {
        var me = this;
        PVECPUDash.ensureStyle();
        me.callParent();

        me.insert(3, { xtype: 'box', colspan: 2, padding: '0 0 8 0' });

        me.insert(4, {
            colspan: 2,
            cls: 'pve-hw-row',
            printBar: false,
            title: gettext('Thermals'),
            textField: 'thermalstate',
            renderer: function(v) {
                try { return PVECPUDash.renderTemps(PVECPUDash.parseState(v)); } catch (e) { return String(e); }
            }
        });

        me.insert(5, {
            colspan: 2,
            cls: 'pve-hw-row',
            printBar: false,
            title: gettext('CPU Frequency'),
            textField: 'thermalstate',
            renderer: function(v) {
                try {
                    me._pveHwData = PVECPUDash.parseState(v);
                    return PVECPUDash.renderCpu(me._pveHwData);
                } catch (e) { return String(e); }
            }
        });

        me.insert(6, {
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
                    width: 160,
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
                    width: 110,
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
                    width: 80,
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
                                        Ext.Msg.alert(gettext('Success'), name);
                                        var store = panel.getStore && panel.getStore();
                                        if (store) store.load();
                                    },
                                    failure: function(r) {
                                        Ext.Msg.alert(gettext('Error'), r.htmlStatus || gettext('Failed'));
                                    }
                                });
                            }
                        };
                    })
                }]
            }]
        });

        me.insert(7, {
            colspan: 2,
            cls: 'pve-hw-row',
            printBar: false,
            title: gettext('Fans'),
            textField: 'thermalstate',
            renderer: function(v) {
                try { return PVECPUDash.renderFans(PVECPUDash.parseState(v)); } catch (e) { return String(e); }
            }
        });

        me.on('afterrender', function() {
            var n = 0;
            var timer = setInterval(function() {
                if (++n > 30) clearInterval(timer);
                var rec = me.getStore && me.getStore() && me.getStore().first && me.getStore().first();
                if (!rec) return;
                var val = rec.get('thermalstate');
                if (!val) return;
                clearInterval(timer);
                try {
                    var data = PVECPUDash.parseState(val);
                    me._pveHwData = data;
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
                } catch (e) { /* ignore */ }
            }, 800);
        });
    }
});
