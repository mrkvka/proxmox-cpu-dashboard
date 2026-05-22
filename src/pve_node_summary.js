/* Proxmox CPU Dashboard - shared UI module */
var PVECPUDash = (function() {
    function ensureStyle() {
        var existing = document.getElementById('pve-hw-dash-style');
        var css = [
            '.pve-hw-row{padding-bottom:14px!important}','.pve-hw-inventory-row .right-aligned{max-width:none!important}',
            '.pve-hw-row .right-aligned{float:none!important;display:block!important;margin-left:155px;text-align:left!important;max-width:calc(100% - 160px)}',
            '.pve-hw-row .left-aligned{width:150px;white-space:nowrap;font-weight:600}',
            '.pve-hw-wrap{font-size:11px;line-height:1.4;color:inherit;max-height:none;overflow:visible;width:100%}','.pve-hw-tab-panel{border:none!important}','.pve-hw-tab-scroll .x-panel-body{overflow-y:auto!important}',
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
            '.pve-hw-row-danger td.applied{color:#dc2626}',
            '@keyframes pve-hw-flash-up{0%{background-color:rgba(35,165,90,.55)}100%{background-color:transparent}}',
            '@keyframes pve-hw-flash-down{0%{background-color:rgba(217,119,6,.55)}100%{background-color:transparent}}',
            '@keyframes pve-hw-flash-changed{0%{background-color:rgba(47,128,237,.45)}100%{background-color:transparent}}',
            '.pve-hw-table td.pve-hw-flash-up{animation:pve-hw-flash-up 1.4s ease-out}',
            '.pve-hw-table td.pve-hw-flash-down{animation:pve-hw-flash-down 1.4s ease-out}',
            '.pve-hw-table td.pve-hw-flash-changed{animation:pve-hw-flash-changed 1.4s ease-out}'
        ].join('');
        if (existing) {
            existing.textContent = css;
            return;
        }
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

    function rowKey(sectionId, param) {
        return String(sectionId || '') + '::' + String(param || '');
    }

    function escAttr(s) {
        return esc(s).replace(/"/g, '&quot;');
    }

    function inventoryRowCount(sections) {
        var n = 0;
        (sections || []).forEach(function(section) {
            n += (section.rows || []).length;
        });
        return n;
    }

    function renderInventory(sections) {
        if (!sections || !sections.length) {
            return '<div class="pve-hw-wrap"><span>—</span></div>';
        }
        var html = ['<div class="pve-hw-wrap">'];
        sections.forEach(function(section) {
            var sid = section.id || section.title || 'section';
            html.push('<div class="pve-hw-h3">' + esc(section.title || section.id) + '</div>');
            html.push('<table class="pve-hw-table" data-pve-hw-section="' + escAttr(sid) + '"><thead><tr>' +
                '<th>' + gettext('Parameter') + '</th>' +
                '<th>' + gettext('Available') + '</th>' +
                '<th>' + gettext('Applied now') + '</th>' +
                '<th>' + gettext('Source') + '</th>' +
                '</tr></thead><tbody>');
            (section.rows || []).forEach(function(row) {
                var applied = cellValue(row);
                var available = row.available != null ? row.available : '—';
                var cls = rowClass(row.parameter, applied);
                html.push('<tr class="' + cls + '" data-pve-hw-row="' + escAttr(rowKey(sid, row.parameter)) + '">' +
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

    function wrapDom(wrapCmp) {
        if (!wrapCmp) return null;
        return wrapCmp.dom ? wrapCmp.dom : wrapCmp;
    }

    function inventoryHost(panel) {
        return panel.down('#pveHwInventoryHost');
    }

    function inventoryWrap(panel) {
        var host = inventoryHost(panel);
        if (!host || !host.getEl) return null;
        return host.getEl().down('.pve-hw-wrap');
    }


    var FLASH_MS = 1400;

    function getPrev(panel) {
        if (!panel._pveHwPrev) panel._pveHwPrev = {};
        return panel._pveHwPrev;
    }

    function clearPrev(panel) {
        panel._pveHwPrev = {};
    }

    function parseNumeric(s) {
        var m = String(s).replace(/,/g, '.').match(/-?\d+(?:\.\d+)?/);
        return m ? parseFloat(m[0]) : null;
    }

    function isInverseMetric(param) {
        var p = String(param).toLowerCase();
        return p.indexOf('temp') >= 0 || p.indexOf('wear') >= 0 ||
            p.indexOf('power') >= 0 || p.indexOf('used') >= 0;
    }

    function flashKind(param, oldStr, newStr) {
        if (oldStr === newStr) return null;
        var o = parseNumeric(oldStr);
        var n = parseNumeric(newStr);
        if (o !== null && n !== null && !isNaN(o) && !isNaN(n) && o !== n) {
            var up = n > o;
            if (isInverseMetric(param)) up = !up;
            return up ? 'pve-hw-flash-up' : 'pve-hw-flash-down';
        }
        return 'pve-hw-flash-changed';
    }

    function flashCell(td, kind) {
        if (!td || !kind) return;
        td.classList.remove('pve-hw-flash-up', 'pve-hw-flash-down', 'pve-hw-flash-changed');
        void td.offsetWidth;
        td.classList.add(kind);
        if (td._pveHwFlashTimer) clearTimeout(td._pveHwFlashTimer);
        td._pveHwFlashTimer = setTimeout(function() {
            td.classList.remove('pve-hw-flash-up', 'pve-hw-flash-down', 'pve-hw-flash-changed');
            td._pveHwFlashTimer = null;
        }, FLASH_MS);
    }

    function updateTableCell(panel, td, rowKeyStr, col, param, newVal) {
        if (!td) return;
        newVal = String(newVal);
        var prev = getPrev(panel);
        var pk = rowKeyStr + '::' + col;
        var oldVal = prev[pk];
        if (oldVal !== undefined && oldVal !== newVal) {
            flashCell(td, flashKind(param, oldVal, newVal));
        }
        prev[pk] = newVal;
        if (td.textContent !== newVal) td.textContent = newVal;
    }

    function buildRowMaps(sections) {
        var byKey = {};
        var byParam = {};
        (sections || []).forEach(function(section) {
            var sid = section.id || section.title || 'section';
            (section.rows || []).forEach(function(row) {
                byKey[rowKey(sid, row.parameter)] = row;
                byParam[String(row.parameter)] = row;
            });
        });
        return { byKey: byKey, byParam: byParam };
    }

    function updateInventoryCells(wrapCmp, sections, panel) {
        var wrap = wrapDom(wrapCmp);
        if (!wrap || !sections || !sections.length) return false;
        var rows = wrap.querySelectorAll('tr[data-pve-hw-row]');
        if (!rows.length) return false;
        var maps = buildRowMaps(sections);
        var updated = 0;
        Ext.Array.forEach(rows, function(tr) {
            var key = tr.getAttribute('data-pve-hw-row') || '';
            var row = maps.byKey[key];
            if (!row) {
                var paramTd = tr.querySelector('td.param');
                if (paramTd) row = maps.byParam[paramTd.textContent];
            }
            if (!row) return;
            updated++;
            var applied = String(cellValue(row));
            var available = String(row.available != null ? row.available : '—');
            var cls = rowClass(row.parameter, applied);
            if (tr.className !== cls) tr.className = cls;
            var rk = key || rowKey('', row.parameter);
            updateTableCell(panel, tr.querySelector('td.avail'), rk, 'avail', row.parameter, available);
            updateTableCell(panel, tr.querySelector('td.applied'), rk, 'applied', row.parameter, applied);
        });
        return updated > 0 && updated >= Math.min(rows.length, inventoryRowCount(sections));
    }

    function saveScroll(panel) {
        var sc = panel.down('#pveHwScroll');
        if (sc && sc.body && sc.body.dom) return sc.body.dom.scrollTop;
        return 0;
    }

    function restoreScroll(panel, st) {
        var sc = panel.down('#pveHwScroll');
        if (sc && sc.body && sc.body.dom) sc.body.dom.scrollTop = st;
    }

    function setInventoryHtml(panel, html) {
        var st = saveScroll(panel);
        var host = inventoryHost(panel);
        if (!host) return;
        host.update(html);
        restoreScroll(panel, st);
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


    var LIVE_POLL_MS = 1000;

    function syncControls(panel, data) {
        var cf = freqOf(data);
        var cpu = cpuOf(data);
        var combo = panel.down('#govCombo');
        if (combo && cf.available_governors && cf.available_governors.length) {
            var store = combo.getStore();
            var needStore = store.getCount() !== cf.available_governors.length;
            if (!needStore) {
                store.each(function(rec, i) {
                    if (rec.get('value') !== cf.available_governors[i]) needStore = true;
                });
            }
            if (needStore) {
                store.loadData(cf.available_governors.map(function(g) {
                    return { value: g, text: g };
                }));
            }
            if (cf.governor && combo.getValue() !== cf.governor) combo.setValue(cf.governor);
        }
        var ff = panel.down('#freqField');
        if (ff && cf.max_khz) ff.setValue(Math.round(cf.max_khz / 1000));
        var of = panel.down('#onlineField');
        if (of && cpu.online) of.setValue(cpu.online);
    }

    function stopLivePoll(panel) {
        if (panel._pveHwPoll) {
            clearInterval(panel._pveHwPoll);
            panel._pveHwPoll = null;
        }

    }

    function startLivePoll(panel) {
        stopLivePoll(panel);
        panel._pveHwPoll = setInterval(function() {
            if (panel.destroyed || panel.isDestroyed) {
                stopLivePoll(panel);
                return;
            }
            if (!panel.isVisible(true)) return;
            fetchLive(panel);
        }, LIVE_POLL_MS);

    }

    function fetchLive(panel, cb) {
        var node = panel.pveSelNode.data.node;
        if (panel._pveHwLivePending) return;
        panel._pveHwLivePending = true;
        Proxmox.Utils.API2Request({
            url: '/nodes/' + encodeURIComponent(node) + '/hwlive',
            method: 'GET',
            failure: function() {
                panel._pveHwLivePending = false;
                if (cb) cb(panel._pveHwData || {});
            },
            success: function(resp) {
                panel._pveHwLivePending = false;
                var data = (resp.result && resp.result.data) ? resp.result.data : (resp.result || {});
                repaintInventory(panel, data);
                syncControls(panel, data);
                if (cb) cb(data);
            }
        });
    }

    function repaintInventory(panel, data, forceFull) {
        panel._pveHwData = data;
        if (!inventoryHost(panel)) return;
        var sections = data && data.inventory;
        var wrap = inventoryWrap(panel);
        if (!forceFull && sections && sections.length && wrap &&
            updateInventoryCells(wrap, sections, panel)) {
            return;
        }
        setInventoryHtml(panel, renderAllInventory(data));
        clearPrev(panel);
        panel._pveHwTableReady = !!(sections && sections.length);
    }

    function fetchFull(panel, cb) {
        var node = panel.pveSelNode.data.node;
        Proxmox.Utils.API2Request({
            url: '/nodes/' + encodeURIComponent(node) + '/hw',
            method: 'GET',
            success: function(resp) {
                var data = (resp.result && resp.result.data) ? resp.result.data : (resp.result || {});
                repaintInventory(panel, data, true);
                if (cb) cb(data);
            },
            failure: function() {
                if (cb) cb(panel._pveHwData || {});
            }
        });
    }

    function needsCpuSafetyConfirm(panel, settings, profile) {
        if (profile === 'emergency') {
            return true;
        }
        var cpu = cpuOf(panel._pveHwData || {});
        if (!cpu.total || !settings.online_cpus) {
            return false;
        }
        return settings.online_cpus < cpu.online;
    }

    function confirmDangerousAction(callback) {
        Ext.Msg.confirm(
            gettext('Warning'),
            gettext('Reducing online CPUs or applying the Emergency profile can disrupt running VMs and workloads. Continue?'),
            function(btn) {
                if (btn === 'yes') {
                    callback();
                }
            }
        );
    }

    function applySettings(panel, settings, options) {
        options = options || {};
        if (!options.confirmed && needsCpuSafetyConfirm(panel, settings, options.profile)) {
            confirmDangerousAction(function() {
                applySettings(panel, settings, { confirmed: true, profile: options.profile });
            });
            return;
        }
        var node = panel.pveSelNode.data.node;
        var base = '/nodes/' + encodeURIComponent(node);
        var done = function() {
            Ext.Msg.alert(gettext('Success'), gettext('Settings applied'));
            fetchFull(panel, function(data) {
                var store = panel.getStore && panel.getStore();
                if (store) store.load();
                syncControls(panel, data || panel._pveHwData || {});
                startLivePoll(panel);
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

    function applyProfile(panel, profileName) {
        var node = panel.pveSelNode.data.node;
        var run = function() {
            Proxmox.Utils.API2Request({
                url: '/nodes/' + encodeURIComponent(node) + '/hwapply',
                method: 'POST',
                params: { node: node, profile: profileName },
                success: function() {
                    Ext.Msg.alert(gettext('Success'), gettext('Profile applied'));
                    fetchFull(panel, function(data) {
                        repaintInventory(panel, data, true);
                        syncControls(panel, data);
                        startLivePoll(panel);
                    });
                },
                failure: function(r) {
                    Ext.Msg.alert(gettext('Error'), r.htmlStatus || gettext('Failed'));
                }
            });
        };
        if (profileName === 'emergency') {
            confirmDangerousAction(run);
        } else {
            run();
        }
    }

    return {
        ensureStyle: ensureStyle,
        parseState: parseState,
        renderAllInventory: renderAllInventory,
        renderInventory: renderInventory,
        fetchFull: fetchFull,
        fetchLive: fetchLive,
        startLivePoll: startLivePoll,
        stopLivePoll: stopLivePoll,
        syncControls: syncControls,
        freqOf: freqOf,
        cpuOf: cpuOf,
        applySettings: applySettings,
        applyProfile: applyProfile,
        confirmDangerousAction: confirmDangerousAction,
        repaintInventory: repaintInventory,
        updateInventoryCells: updateInventoryCells,
        setInventoryHtml: setInventoryHtml,
        inventoryWrap: inventoryWrap,
        saveScroll: saveScroll,
        restoreScroll: restoreScroll
    };
})();
