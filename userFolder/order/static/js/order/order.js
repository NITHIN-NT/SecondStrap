// =======================================================
// MODAL CONTROLS
// =======================================================

function openReturnModal() {
    document.getElementById('returnModal').style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeReturnModal() {
    document.getElementById('returnModal').style.display = 'none';
    document.body.style.overflow = 'auto';
}

function openCancelReturnModal() {
    document.getElementById('cancelReturnModal').style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeCancelReturnModal() {
    document.getElementById('cancelReturnModal').style.display = 'none';
    document.body.style.overflow = 'auto';
}

function openCancelOrderModal() {
    document.getElementById('cancelOrderModal').style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeCancelOrderModal() {
    document.getElementById('cancelOrderModal').style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Global click listener to close modals on backdrop click
window.onclick = function (event) {
    ['returnModal', 'cancelReturnModal', 'cancelOrderModal'].forEach(id => {
        const modal = document.getElementById(id);
        if (modal && event.target === modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    });
};

// =======================================================
// RETURN MODAL LOGIC
// =======================================================

function setReturnMode(mode, btn) {
    const modal = document.getElementById('returnModal');
    modal.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    document.getElementById('return_mode').value = mode;

    const globalSection = document.getElementById('global_reason_section');
    const subtitle = document.getElementById('list_subtitle');
    const list = modal.querySelector('.return-items-list');
    const checkboxes = modal.querySelectorAll('.item-checkbox');

    if (mode === 'all') {
        globalSection.style.display = 'block';
        subtitle.style.display = 'none';
        list.classList.add('disabled-area');
        checkboxes.forEach(cb => cb.checked = true);
    } else {
        globalSection.style.display = 'none';
        subtitle.style.display = 'block';
        list.classList.remove('disabled-area');
        checkboxes.forEach(cb => cb.checked = false);
        modal.querySelectorAll('.return-reason-box').forEach(b => b.style.display = 'none');
        modal.querySelectorAll('.return-item-row').forEach(r => r.classList.remove('selected'));
    }
}

function toggleReturnReason(itemId) {
    if (document.getElementById('return_mode').value === 'all') return;

    const cb = document.getElementById(`check_${itemId}`);
    const box = document.getElementById(`reason_container_${itemId}`);
    const row = document.getElementById(`row_${itemId}`);
    const reason = document.getElementById(`reason_input_${itemId}`);
    const note = document.getElementById(`note_input_${itemId}`);

    if (cb.checked) {
        box.style.display = 'block';
        row.classList.add('selected');
        reason.disabled = false;
        note.disabled = false;
    } else {
        box.style.display = 'none';
        row.classList.remove('selected');
        reason.disabled = true;
        note.disabled = true;
        reason.value = '';
        note.value = '';
    }
}

// =======================================================
// CANCEL MODAL LOGIC
// =======================================================

function setCancelMode(mode, btn) {
    const modal = document.getElementById('cancelOrderModal');
    modal.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    document.getElementById('cancel_mode').value = mode;

    const globalSection = document.getElementById('cancel_global_section');
    const subtitle = document.getElementById('cancel_list_subtitle');
    const list = modal.querySelector('.return-items-list');

    // Reset fields
    modal.querySelectorAll('.item-checkbox').forEach(cb => cb.checked = false);
    modal.querySelectorAll('select, textarea').forEach(el => {
        el.disabled = true;
        el.value = '';
    });
    // Ensure global fields are re-enabled if mode is 'all'
    document.getElementById('cancel_global_reason').disabled = false;
    document.getElementById('cancel_global_note').disabled = false;

    modal.querySelectorAll('.return-reason-box').forEach(b => b.style.display = 'none');
    modal.querySelectorAll('.return-item-row').forEach(r => r.classList.remove('selected'));

    if (mode === 'all') {
        globalSection.style.display = 'block';
        subtitle.style.display = 'none';
        list.classList.add('disabled-area');
    } else {
        globalSection.style.display = 'none';
        subtitle.style.display = 'block';
        list.classList.remove('disabled-area');
    }
}

function toggleCancelInput(itemId) {
    if (document.getElementById('cancel_mode').value === 'all') return;

    const cb = document.getElementById(`cancel_check_${itemId}`);
    const box = document.getElementById(`cancel_input_container_${itemId}`);
    const row = document.getElementById(`cancel_row_${itemId}`);
    const reason = document.getElementById(`cancel_reason_${itemId}`);
    const note = document.getElementById(`cancel_note_${itemId}`);

    if (cb.checked) {
        box.style.display = 'block';
        row.classList.add('selected');
        reason.disabled = false;
        note.disabled = false;
    } else {
        box.style.display = 'none';
        row.classList.remove('selected');
        reason.disabled = true;
        note.disabled = true;
        reason.value = '';
        note.value = '';
    }
}

// =======================================================
// AXIOS SUBMISSIONS
// =======================================================

// 1. Return Form Submission
const returnForm = document.getElementById('returnForm');
if (returnForm) {
    returnForm.addEventListener('submit', e => {
        e.preventDefault();

        const mode = document.getElementById('return_mode').value;
        const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
        let payload = [];

        if (mode === 'all') {
            const reason = document.getElementById('global_reason').value;
            const note = document.getElementById('global_note').value;
            if (!reason) return toastr.error('Please select a return reason');

            document.querySelectorAll('#returnModal .item-checkbox').forEach(cb => {
                payload.push({ item_id: cb.value, reason: reason, note: note });
            });
        } else {
            const checked = document.querySelectorAll('#returnModal input[name="selected_items"]:checked');
            if (!checked.length) return toastr.error('Select at least one item to return');

            for (let cb of checked) {
                const r = document.getElementById(`reason_input_${cb.value}`).value;
                const n = document.getElementById(`note_input_${cb.value}`).value;
                if (!r) return toastr.error('Select reason for all checked items');
                payload.push({ item_id: cb.value, reason: r, note: n });
            }
        }

        axios.post(returnForm.action, { returns: payload }, {
            headers: { 'X-CSRFToken': csrf }
        }).then(() => {
            toastr.success('Return request submitted');
            setTimeout(() => location.reload(), 1200);
        }).catch(err => {
            toastr.error(err.response?.data?.message || 'Something went wrong');
        });
    });
}

// 2. Cancel Form Submission
const cancelForm = document.getElementById('cancelOrderForm');
if (cancelForm) {
    cancelForm.addEventListener('submit', e => {
        e.preventDefault();

        const mode = document.getElementById('cancel_mode').value;
        const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
        let payload = [];

        if (mode === 'all') {
            const reason = document.getElementById('cancel_global_reason').value;
            const note = document.getElementById('cancel_global_note').value;

            if (!reason || !note.trim()) return toastr.error('Please provide a reason and description');

            document.querySelectorAll('#cancelOrderModal .item-checkbox').forEach(cb => {
                payload.push({ item_id: cb.value, reason: reason, note: note });
            });
        } else {
            const checked = document.querySelectorAll('#cancelOrderModal input[name="selected_items"]:checked');
            if (!checked.length) return toastr.error('Select at least one item to cancel');

            for (let cb of checked) {
                const reason = document.getElementById(`cancel_reason_${cb.value}`).value;
                const note = document.getElementById(`cancel_note_${cb.value}`).value;

                if (!reason || !note.trim()) {
                    return toastr.error('Reason & description required');
                }

                payload.push({
                    item_id: cb.value,
                    reason: reason,
                    note: note
                });
            }
        }

        axios.post(cancelForm.action, { cancels: payload }, {
            headers: { 'X-CSRFToken': csrf }
        }).then(() => {
            toastr.success('Cancellation successful');
            setTimeout(() => location.reload(), 1200);
        }).catch(err => {
            toastr.error(err.response?.data?.message || 'Something went wrong');
        });
    });
}