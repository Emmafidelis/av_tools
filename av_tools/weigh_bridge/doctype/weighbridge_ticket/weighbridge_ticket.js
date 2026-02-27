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

const save_after_weight_capture = (frm) => {
  if (!frm.is_dirty() || frm._weight_save_in_progress) {
    return Promise.resolve();
  }

  frm._weight_save_in_progress = true;
  const save_result = frm.save();
  if (save_result && typeof save_result.finally === "function") {
    return save_result.finally(() => {
      frm._weight_save_in_progress = false;
    });
  }
  frm._weight_save_in_progress = false;
  return Promise.resolve();
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
  const rawText = (text || "").trim();
  if (!rawText) {
    return null;
  }

  let data;
  try {
    data = JSON.parse(rawText);
  } catch (err) {
    data = null;
  }

  if (data) {
    const directWeight =
      data.weight ??
      data.Weight ??
      data.value ??
      data.Value ??
      (data.data && data.data.weight);

    if (directWeight != null) {
      return {
        weight: flt(directWeight),
        raw: data.raw || String(directWeight),
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
    return parse_valpoids(rawText);
  } catch (err) {
    const m = rawText.match(/[-+]?\d*\.?\d+/);
    if (m) {
      return {
        weight: flt(m[0]),
        raw: rawText,
      };
    }
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
          contentType: response.headers.get("content-type"),
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
          frappe.msgprint(
            __(
              "Missing weight in response from {0} (HTTP {1}).",
              [result.url, result.status]
            )
          );
          // eslint-disable-next-line no-console
          console.error("Weighbridge raw response", result);
          return;
        }

        Promise.resolve(frm.set_value(target_field, data.weight))
          .then(() => frm.set_value(time_field, frappe.datetime.now_datetime()))
          .then(() => {
            set_net_weight(frm);
            return save_after_weight_capture(frm);
          })
          .then(() => {
            const label =
              target_field === "tare_weight"
                ? __("Tare Weight")
                : __("Gross Weight");
            frappe.show_alert(
              {
                message: __("{0} captured: {1}", [label, format_number(data.weight)]),
                indicator: "green",
              },
              5
            );
          });
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
