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

const ensure_gateway_payload = (frm, callback) => {
  if (frm._gateway_url && frm._gateway_payload) {
    callback();
    return;
  }

  frappe.call({
    method: "av_tools.weigh_bridge.api.get_gateway_payload",
    callback: (r) => {
      if (!r.message) {
        frappe.msgprint(__("Weighbridge Settings are not configured."));
        return;
      }
      frm._gateway_url = (r.message.gateway_url || "").replace(/\/+$/, "");
      frm._gateway_payload = r.message.payload || {};
      frm._read_weight_url =
        (r.message.payload || {}).read_url || r.message.read_weight_url || "";
      callback();
    },
  });
};

const parse_valpoids = (xmlText) => {
  const match = xmlText.match(
    /<id>ValPoids<\/id><value>\s*([^<]+)<\/value>/i
  );
  if (!match) {
    throw new Error("ValPoids not found in response.");
  }
  const rawValue = match[1].trim();
  const numberMatch = rawValue.match(/[-+]?\d*\.?\d+/);
  if (!numberMatch) {
    throw new Error("No numeric weight found in response.");
  }
  return {
    weight: flt(numberMatch[0]),
    raw: rawValue,
  };
};

const read_weight_client = (frm, target_field, time_field) => {
  const items = frm.doc.items || [];
  if (!items.length) {
    frappe.msgprint(__("Please add at least one item before reading weight."));
    return;
  }

  ensure_gateway_payload(frm, () => {
    if (frm._read_weight_url) {
      fetch(frm._read_weight_url, { method: "GET", cache: "no-store" })
        .then((response) =>
          response.text().then((text) => ({
            ok: response.ok,
            status: response.status,
            text,
          }))
        )
        .then((result) => {
          if (!result.ok) {
            frappe.msgprint(result.text || `HTTP ${result.status}`);
            return;
          }
          const data = parse_valpoids(result.text || "");
          frm.set_value(target_field, data.weight);
          frm.set_value(time_field, frappe.datetime.now_datetime());
          set_net_weight(frm);
        })
        .catch((error) => {
          frappe.msgprint(error.message);
          // eslint-disable-next-line no-console
          console.error(error);
        });
      return;
    }

    if (!frm._gateway_url) {
      frappe.msgprint(__("Read Weight URL or Gateway URL is not configured."));
      return;
    }

    const url = `${frm._gateway_url}/read_weight`;

    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(frm._gateway_payload || {}),
    })
      .then((response) =>
        response.text().then((text) => ({
          ok: response.ok,
          status: response.status,
          text,
        }))
      )
      .then((result) => {
        if (!result.ok) {
          frappe.msgprint(result.text || `HTTP ${result.status}`);
          return;
        }

        let data = {};
        try {
          data = JSON.parse(result.text || "{}");
        } catch (err) {
          frappe.msgprint(result.text || "Invalid JSON response.");
          return;
        }

        if (data.weight == null) {
          frappe.msgprint(result.text || "Missing weight in response.");
          return;
        }
        frm.set_value(target_field, data.weight);
        frm.set_value(time_field, frappe.datetime.now_datetime());
        set_net_weight(frm);
      })
      .catch((error) => {
        frappe.msgprint(error.message);
        // eslint-disable-next-line no-console
        console.error(error);
      });
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
