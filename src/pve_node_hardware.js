/* Proxmox CPU Dashboard - Hardware tab */
Ext.define('PVE.node.HardwareView', {
    extend: 'Ext.panel.Panel',
    alias: 'widget.pveNodeHardware',

    layout: { type: 'vbox', align: 'stretch' },
    border: false,
    bodyPadding: 0,

    initComponent: function() {
        var me = this;
        PVECPUDash.ensureStyle();

        me.items = [{
            xtype: 'container',
            itemId: 'pve-hw-controls',
            cls: 'pve-hw-panel',
            margin: '8 10 8 10',
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
                        var panel = btn.up('pveNodeHardware');
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
                                var panel = this.up('pveNodeHardware');
                                var node = panel.pveSelNode.data.node;
                                Proxmox.Utils.API2Request({
                                    url: '/nodes/' + encodeURIComponent(node) + '/hwapply',
                                    method: 'POST',
                                    params: { node: node, profile: name },
                                    success: function() {
                                        PVECPUDash.fetchFull(panel, function(data) {
                                            PVECPUDash.repaintInventory(panel, data, true);
                                            PVECPUDash.syncControls(panel, data);
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
                        var panel = btn.up('pveNodeHardware');
                        PVECPUDash.fetchFull(panel, function(data) {
                            PVECPUDash.repaintInventory(panel, data, true);
                            PVECPUDash.syncControls(panel, data);
                        });
                    }
                }]
            }]
        }, {
            xtype: 'panel',
            itemId: 'pveHwScroll',
            flex: 1,
            cls: 'pve-hw-tab-scroll',
            layout: 'fit',
            border: false,
            bodyPadding: '4 10 12 10',
            scrollable: true,
            items: [{
                xtype: 'box',
                itemId: 'pveHwInventoryHost',
                html: '<div class="pve-hw-wrap">' + gettext('Loading hardware inventory…') + '</div>'
            }]
        }];

        me.callParent();

        me.on('activate', function() {
            if (!me._pveHwLoaded) {
                PVECPUDash.fetchFull(me, function(data) {
                    PVECPUDash.repaintInventory(me, data, true);
                    PVECPUDash.syncControls(me, data);
                    me._pveHwLoaded = true;
                });
            }
            PVECPUDash.startLivePoll(me);
        });

        me.on('deactivate', function() {
            PVECPUDash.stopLivePoll(me);
        });

        me.on('destroy', function() {
            PVECPUDash.stopLivePoll(me);
            me._pveHwLoaded = false;
            me._pveHwTableReady = false;
        });
    },
});

Ext.define('PVE.node.Config', {
    override: 'PVE.node.Config',

    initComponent: function() {
        var me = this;
        me.callParent(arguments);
        var caps = Ext.state.Manager.get('GuiCap');
        if (!caps.nodes || !caps.nodes['Sys.Audit']) {
            return;
        }
        if (me.savedItems && me.savedItems.pvehardware) {
            return;
        }
        me.insertNodes([{
            xtype: 'pveNodeHardware',
            title: gettext('Hardware'),
            iconCls: 'fa fa-microchip',
            itemId: 'pvehardware',
        }]);
    },
});
