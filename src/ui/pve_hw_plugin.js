/* Minimal ExtJS plugin: Node → Hardware + Guests tabs (not VM/CT). Requires pve_hw_tab.js + pve_hw_guests.js */
Ext.define('PVE.panel.Config', {
    override: 'PVE.panel.Config',

    insertNodes: function(items) {
        var me = this;
        var list = items || [];

        /* PVE.node.Config only — qemu/lxc also extend PVE.panel.Config and have itemId "summary" */
        if (me.$className !== 'PVE.node.Config') {
            return this.callParent([list]);
        }

        var caps = Ext.state.Manager.get('GuiCap');
        if (caps.nodes && caps.nodes['Sys.Audit']) {
            var expanded = [];
            var hasHw = !!(me.savedItems && me.savedItems.pvehardware);
            var hasGuests = !!(me.savedItems && me.savedItems.pveguests);

            list.forEach(function(item) {
                expanded.push(item);
                if (item && item.xtype === 'pveNodeSummary') {
                    if (!hasHw) {
                        expanded.push({
                            xtype: 'pveNodeHardware',
                            title: gettext('Hardware'),
                            iconCls: 'fa fa-microchip',
                            itemId: 'pvehardware',
                        });
                    }
                    if (!hasGuests) {
                        expanded.push({
                            xtype: 'pveNodeGuests',
                            title: gettext('Guests'),
                            iconCls: 'fa fa-server',
                            itemId: 'pveguests',
                        });
                    }
                }
            });
            list = expanded;
        }

        return this.callParent([list]);
    },
});
