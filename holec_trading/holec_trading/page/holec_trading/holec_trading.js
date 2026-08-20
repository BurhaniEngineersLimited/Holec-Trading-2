frappe.pages['holec-trading'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Holec Trading'),
        single_column: true
    });

    // Holec Trading Module DocTypes
    const doctypes = [
        'Buy Ticket',
        'Lot',
        'Storage Stack',
        'Cost Ledger Entry',
        'Charge Master',
        'Lot Event Log',
        'Rail Routing Band',
        'Origin Area',
        'Origin County'
    ];

    // Render 2-Column Split Layout
    let $layout = $(`
        <div class="row holec-split-layout">
            <div class="col-md-3 holec-sidebar">
                <div class="list-group sidebar-doctype-list"></div>
            </div>
            <div class="col-md-9 holec-content-area">
                <div class="card p-3 shadow-sm" id="doctype-view-container">
                    <p class="text-muted text-center my-4">${__('Select a DocType from the left menu')}</p>
                </div>
            </div>
        </div>
    `).appendTo(page.main);

    // Populate Sidebar
    let $sidebar = $layout.find('.sidebar-doctype-list');
    doctypes.forEach((dt) => {
        let $item = $(`
            <a href="javascript:void(0)" class="list-group-item list-group-item-action doctype-nav-item d-flex align-items-center justify-content-between" data-doctype="${dt}">
                <span class="doctype-label font-weight-bold">${__(dt)}</span>
                <i class="fa fa-chevron-right text-muted" style="font-size: 11px;"></i>
            </a>
        `);

        $item.on('click', function() {
            $sidebar.find('.doctype-nav-item').removeClass('active');
            $(this).addClass('active');
            load_doctype_view(dt);
        });

        $sidebar.append($item);
    });

    // Auto-load the first DocType (Buy Ticket)
    if (doctypes.length > 0) {
        $sidebar.find('.doctype-nav-item').first().trigger('click');
    }

    // Load dynamic list view on the right
    function load_doctype_view(doctype) {
        let $container = $('#doctype-view-container');
        $container.empty().html(`
            <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom">
                <h4 class="mb-0 font-weight-bold text-dark">${__(doctype)}</h4>
                <div class="btn-group">
                    <button class="btn btn-sm btn-primary" id="btn-new-doc">
                        <i class="fa fa-plus mr-1"></i> ${__('Add')} ${__(doctype)}
                    </button>
                    <a href="/app/${frappe.router.slug(doctype)}" class="btn btn-sm btn-outline-secondary">
                        <i class="fa fa-external-link mr-1"></i> ${__('Full List')}
                    </a>
                </div>
            </div>
            <div id="doctype-list-wrapper">
                <div class="text-center py-4 text-muted"><i class="fa fa-spinner fa-spin"></i> Loading records...</div>
            </div>
        `);

        $container.find('#btn-new-doc').on('click', () => {
            frappe.new_doc(doctype);
        });

        frappe.model.with_doctype(doctype, function() {
            let meta = frappe.get_meta(doctype);
            let columns = ['name'];

            // Fetch standard list fields
            meta.fields.filter(f => f.in_list_view && f.fieldtype !== 'Table').slice(0, 4).forEach(f => {
                columns.push(f.fieldname);
            });
            columns.push('modified');

            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: doctype,
                    fields: columns,
                    limit_page_length: 20,
                    order_by: 'modified desc'
                },
                callback: function(r) {
                    let data = r.message || [];
                    render_table($container.find('#doctype-list-wrapper'), doctype, columns, data);
                }
            });
        });
    }

    function render_table($parent, doctype, columns, data) {
        if (!data.length) {
            $parent.html(`
                <div class="text-center text-muted py-5">
                    <i class="fa fa-folder-open-o fa-2x mb-2"></i>
                    <p class="mb-0">${__('No records found for')} <strong>${__(doctype)}</strong></p>
                </div>
            `);
            return;
        }

        let table_html = `
            <div class="table-responsive">
                <table class="table table-hover table-bordered mb-0">
                    <thead class="thead-light">
                        <tr>
                            ${columns.map(c => `<th>${frappe.unscrub(c)}</th>`).join('')}
                            <th class="text-center" style="width: 100px;">${__('Action')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.map(row => `
                            <tr>
                                ${columns.map(c => `<td>${row[c] !== null && row[c] !== undefined ? row[c] : '-'}</td>`).join('')}
                                <td class="text-center">
                                    <a href="/app/${frappe.router.slug(doctype)}/${encodeURIComponent(row.name)}" class="btn btn-xs btn-outline-primary">
                                        ${__('Open')}
                                    </a>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        $parent.html(table_html);
    }
};