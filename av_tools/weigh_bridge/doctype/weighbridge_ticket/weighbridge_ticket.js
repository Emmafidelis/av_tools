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

const ensure_gateway_payload = (frm, callback) => {
  if (frm._gateway_url && frm._gateway_payload) {
    callback();
    return;
  }

  frappe.call({
    method: "av_tools.weigh_bridge.api.get_gateway_payload",
    callback: (r) => {
      if (!r.message || !r.message.gateway_url) {
        frappe.msgprint(__("Gateway URL is not configured."));
        return;
      }
      frm._gateway_url = r.message.gateway_url.replace(/\/+$/, "");
      frm._gateway_payload = r.message.payload || {};
      callback();
    },
  });
};

const read_weight_client = (frm, target_field, time_field) => {
  ensure_gateway_payload(frm, () => {
    const url = `${frm._gateway_url}/read_weight`;

    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(frm._gateway_payload || {}),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Gateway error: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        if (!data || data.weight == null) {
          frappe.msgprint(__("No weight received from the gateway."));
          return;
        }
        frm.set_value(target_field, data.weight);
        frm.set_value(time_field, frappe.datetime.now_datetime());
        set_net_weight(frm);
      })
      .catch((error) => {
        frappe.msgprint(
          __(
            "Failed to read weight. If this is a HTTPS site, the gateway must be HTTPS or tunneled."
          )
        );
        // Log error for debugging without breaking UI.
        // eslint-disable-next-line no-console
        console.error(error);
      });
  });
};

frappe.ui.form.on("Weighbridge Ticket", {
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
