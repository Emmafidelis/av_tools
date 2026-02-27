// Copyright (c) 2026, Aakvatech and contributors
// For license information, please see license.txt

const DEFAULT_UOM = "Kg";

const distribute_net_weight = (frm, netWeight) => {
  const items = frm.doc.items || [];
  if (!items.length) {
    return;
  }

  const totalQty = items.reduce((sum, row) => sum + flt(row.qty || 0), 0);
  const useProportional = totalQty > 0;
  const perItem = items.length ? flt(netWeight) / items.length : 0;

  items.forEach((row) => {
    const qty = useProportional
      ? (flt(row.qty || 0) / totalQty) * flt(netWeight)
      : perItem;
    frappe.model.set_value(row.doctype, row.name, "qty", qty);
    frappe.model.set_value(row.doctype, row.name, "uom", DEFAULT_UOM);
  });
};

const set_net_weight = (frm) => {
  if (frm.doc.tare_weight != null && frm.doc.gross_weight != null) {
    const net = flt(frm.doc.gross_weight) - flt(frm.doc.tare_weight);
    frm.set_value("net_weight", net);
    distribute_net_weight(frm, net);
  }
};

const read_weight_client = (frm, target_field, time_field) => {
  const items = frm.doc.items || [];
  if (!items.length) {
    frappe.msgprint(__("Please add at least one item before reading weight."));
    return;
  }
  frappe.call({
    method: "av_tools.weigh_bridge.api.read_weight",
    args: { mode: target_field },
    callback: (r) => {
      if (!r.message) {
        frappe.msgprint(__("Failed to read weight."));
        return;
      }
      if (r.message.weight == null) {
        frappe.msgprint(__("Missing weight in response."));
        return;
      }
      frm.set_value(target_field, r.message.weight);
      frm.set_value(time_field, frappe.datetime.now_datetime());
      set_net_weight(frm);
    },
  });
};

const toggle_read_buttons = (frm) => {
  const hasItems = (frm.doc.items || []).length > 0;
  frm.set_df_property("read_tare", "read_only", !hasItems);
  frm.set_df_property("read_gross", "read_only", !hasItems);
};

frappe.ui.form.on("Weighbridge Ticket", {
  refresh(frm) {
    toggle_read_buttons(frm);
  },
  items_add(frm) {
    toggle_read_buttons(frm);
  },
  items_remove(frm) {
    toggle_read_buttons(frm);
  },
  items_on_form_rendered(frm) {
    toggle_read_buttons(frm);
  },
  read_tare(frm) {
    read_weight_client(frm, "tare_weight", "tare_time");
  },
  read_gross(frm) {
    read_weight_client(frm, "gross_weight", "gross_time");
  },
  tare_weight(frm) {
    set_net_weight(frm);
  },
  gross_weight(frm) {
    set_net_weight(frm);
  },
});
