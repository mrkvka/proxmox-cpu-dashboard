/* Minimal ExtJS plugin: register Node → Hardware tab (requires pve_hw_tab.js) */
Ext.define('PVE.panel.Config', {
    override: 'PVE.panel.Config',

    insertNodes: function(items) {
        var me = this;
        var caps = Ext.state.Manager.get('GuiCap');
        var list = items || [];

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
                if (item && item.itemId === 'summary') {
                    expanded.push(hwTab);
                }
            });
            list = expanded;
        }

        return this.callParent([list]);
    },
});
