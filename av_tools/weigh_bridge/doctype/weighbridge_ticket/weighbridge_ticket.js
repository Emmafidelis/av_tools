// Copyright (c) 2026, Aakvatech and contributors
// For license information, please see license.txt

const set_net_weight = (frm) => {
  if (frm.doc.tare_weight != null && frm.doc.gross_weight != null) {
    frm.set_value(
      "net_weight",
      flt(frm.doc.gross_weight) - flt(frm.doc.tare_weight)
    );
  }
};

const read_weight = (frm, target_field, time_field, mode) => {
  frappe.call({
    method: "av_tools.weigh_bridge.api.read_weight",
    args: { mode },
    freeze: true,
    freeze_message: __("Reading weight..."),
    callback: (r) => {
      if (!r.message || r.message.weight == null) {
        frappe.msgprint(__("No weight received from the gateway."));
        return;
      }

      frm.set_value(target_field, r.message.weight);
      frm.set_value(time_field, frappe.datetime.now_datetime());
      set_net_weight(frm);
    },
  });
};

frappe.ui.form.on("Weighbridge Ticket", {
  read_tare(frm) {
    read_weight(frm, "tare_weight", "tare_time", "tare");
  },
  read_gross(frm) {
    read_weight(frm, "gross_weight", "gross_time", "gross");
  },
  tare_weight(frm) {
    set_net_weight(frm);
  },
  gross_weight(frm) {
    set_net_weight(frm);
  },
});
