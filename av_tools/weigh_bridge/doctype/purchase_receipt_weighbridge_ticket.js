const set_weighbridge_query = (frm) => {
  if (!frm.fields_dict.weighbridge_ticket) {
    return;
  }

  const query = () => {
    const filters = {
      document_type: "Purchase Receipt",
      docstatus: 1,
    };

    return { filters };
  };

  frm.set_query("weighbridge_ticket", query);
  frm.fields_dict.weighbridge_ticket.get_query = query;
};

const apply_ticket_items = (frm, ticket) => {
  const items = ticket.items || [];
  if (!items.length) {
    frappe.msgprint(__("Selected Weighbridge Ticket has no items."));
    return;
  }

  frm.clear_table("items");
  items.forEach((row) => {
    const child = frm.add_child("items");
    child.item_code = row.item_code;
    if (row.qty != null) {
      child.qty = row.qty;
    }
    if (row.uom) {
      child.uom = row.uom;
    }
  });
  frm.refresh_field("items");
};

const handle_ticket_change = (frm) => {
  if (!frm.doc.weighbridge_ticket) {
    return;
  }

  frappe.call({
    method: "frappe.client.get",
    args: {
      doctype: "Weighbridge Ticket",
      name: frm.doc.weighbridge_ticket,
    },
    callback: (r) => {
      if (!r.message) {
        frappe.msgprint(__("Unable to load Weighbridge Ticket."));
        return;
      }
      apply_ticket_items(frm, r.message);
    },
  });
};

frappe.ui.form.on("Purchase Receipt", {
  onload(frm) {
    set_weighbridge_query(frm);
  },

});
