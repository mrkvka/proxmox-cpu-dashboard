/* Minimal ExtJS plugin: Node → Hardware tab only (not VM/CT). Requires pve_hw_tab.js */
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
        if (caps.nodes && caps.nodes['Sys.Audit'] && !(me.savedItems && me.savedItems.pvehardware)) {
            var hwTab = {
                xtype: 'pveNodeHardware',
                title: gettext('Hardware'),
                iconCls: 'fa fa-microchip',
                itemId: 'pvehardware',
            };
            var expanded = [];
            list.forEach(function(item) {
                expanded.push(item);
                if (item && item.xtype === 'pveNodeSummary') {
                    expanded.push(hwTab);
                }
            });
            list = expanded;
        }

        return this.callParent([list]);
    },
});
