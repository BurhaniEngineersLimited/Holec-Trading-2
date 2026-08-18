// Copyright (c) 2026, Holec
// Adds the "Advance State" button, calling the server-side
// advance_lot_state() function in lot.py rather than letting the user
// edit the state field directly.

frappe.ui.form.on("Lot", {
	refresh(frm) {
		if (frm.is_new()) return;

		const next_state_map = {
			"Ticket": "Intake",
			"Intake": "Lot",
			"Lot": "Position",
			"Position": "Invoiced",
			"Invoiced": "Settled",
		};

		const next_state = next_state_map[frm.doc.state];

		if (next_state) {
			frm.add_custom_button(__("Advance to {0}", [next_state]), () => {
				frappe.confirm(
					__("Advance this Lot from {0} to {1}? This will post any required cost entries and cannot be undone directly - only reversed.", [frm.doc.state, next_state]),
					() => {
						frappe.call({
							method: "holec_trading.holec_trading.doctype.lot.lot.advance_lot_state",
							args: { lot_name: frm.doc.name },
							freeze: true,
							freeze_message: __("Advancing state..."),
							callback: (r) => {
								if (r.message) {
									frappe.show_alert({
										message: __("Lot advanced to {0}", [r.message.new_state]),
										indicator: "green",
									});
									frm.reload_doc();
								}
							},
						});
					}
				);
			}).addClass("btn-primary");
		} else {
			frm.dashboard.set_headline_alert(
				`<div class="indicator-pill green">${__("Settled - lifecycle complete")}</div>`
			);
		}

		// Surface the moisture approval flag prominently rather than
		// leaving it buried in a checkbox.
		if (frm.doc.requires_moisture_approval) {
			frm.dashboard.set_headline_alert(
				`<div class="indicator-pill orange">${__("Moisture over 20% - requires Minal's approval before proceeding")}</div>`
			);
		}

		if (frm.doc.commingled) {
			frm.dashboard.set_headline_alert(
				`<div class="indicator-pill orange">${__("Storage stack is commingled - origin is proportional, not exact, for this Lot")}</div>`
			);
		}
	},

	storage_stack(frm) {
		// Trigger the commingling check when the user sets/changes stack.
		if (frm.doc.storage_stack) {
			frm.trigger("run_commingling_check");
		}
	},

	run_commingling_check(frm) {
		frappe.call({
			method: "check_commingling",
			doc: frm.doc,
			callback: () => frm.refresh_field("commingled"),
		});
	},
});
