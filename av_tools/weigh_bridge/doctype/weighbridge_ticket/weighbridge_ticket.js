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
  // Always refresh from settings in case URL was updated while form is open.
  frappe.call({
    method: "av_tools.weigh_bridge.api.get_gateway_payload",
    callback: (r) => {
      if (!r.message) {
        frappe.msgprint(__("Weighbridge Settings are not configured."));
        return;
      }
      frm._read_weight_url = (r.message.read_weight_url || "").replace(/\/+$/, "");
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

const parse_weight_from_raw_text = (text) => {
  let data;
  try {
    data = JSON.parse(text || "{}");
  } catch (err) {
    data = null;
  }

  if (data) {
    if (data.weight != null) {
      return {
        weight: flt(data.weight),
        raw: data.raw || String(data.weight),
      };
    }

    if (typeof data.raw === "string") {
      const m = data.raw.match(/[-+]?\d*\.?\d+/);
      if (m) {
        return {
          weight: flt(m[0]),
          raw: data.raw,
        };
      }
    }
  }

  try {
    return parse_valpoids(text || "");
  } catch (err) {
    return null;
  }
};

const read_weight_client = (frm, target_field, time_field) => {
  const items = frm.doc.items || [];
  if (!items.length) {
    frappe.msgprint(__("Please add at least one item before reading weight."));
    return;
  }

  ensure_gateway_payload(frm, () => {
    if (!frm._read_weight_url) {
      frappe.msgprint(__("Read Weight URL is not configured."));
      return;
    }

    const call_url = (url) =>
      fetch(url, { method: "GET", cache: "no-store" }).then((response) =>
        response.text().then((text) => ({
          ok: response.ok,
          status: response.status,
          text,
          url,
        }))
      );

    call_url(frm._read_weight_url)
      .then((response) =>
        !response.ok
          ? response
          : (() => {
              const parsed = parse_weight_from_raw_text(response.text || "");
              if (parsed || /\/read_weight$/i.test(response.url)) {
                return response;
              }
              const retry_url = `${response.url.replace(/\/+$/, "")}/read_weight`;
              return call_url(retry_url);
            })()
      )
      .then((result) => {
        if (!result.ok) {
          frappe.msgprint(result.text || `HTTP ${result.status}`);
          return;
        }

        const data = parse_weight_from_raw_text(result.text || "");

        if (!data || data.weight == null) {
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
