 // --- MODAL CONTROLS ---
    function openReturnModal() {
        document.getElementById('returnModal').style.display = 'block';
        document.body.style.overflow = 'hidden';
    }

    function closeReturnModal() {
        document.getElementById('returnModal').style.display = 'none';
        document.body.style.overflow = 'auto';
    }

    window.onclick = function(event) {
        if (event.target == document.getElementById('returnModal')) {
            closeReturnModal();
        }
    }

    // --- TAB SWITCHING LOGIC ---
    function setReturnMode(mode, btnElement) {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        btnElement.classList.add('active');

        document.getElementById('return_mode').value = mode;

        const globalSection = document.getElementById('global_reason_section');
        const listSubtitle = document.getElementById('list_subtitle');
        const checkboxes = document.querySelectorAll('.item-checkbox');
        
        if (mode === 'all') {
            globalSection.style.display = 'block';
            listSubtitle.style.display = 'none';
            checkboxes.forEach(cb => { cb.checked = true; });
            document.querySelector('.return-items-list').classList.add('disabled-area');
            document.querySelectorAll('.return-reason-box').forEach(box => box.style.display = 'none');
        } else {
            globalSection.style.display = 'none';
            listSubtitle.style.display = 'block';
            checkboxes.forEach(cb => { cb.checked = false; });
            document.querySelector('.return-items-list').classList.remove('disabled-area');
            document.querySelectorAll('.return-reason-box').forEach(box => box.style.display = 'none');
            document.querySelectorAll('.return-item-row').forEach(row => row.classList.remove('selected'));
        }
    }

    // --- INDIVIDUAL TOGGLE LOGIC ---
    function toggleReturnReason(itemId) {
        const mode = document.getElementById('return_mode').value;
        if(mode === 'all') return; 

        const checkbox = document.getElementById('check_' + itemId);
        const reasonContainer = document.getElementById('reason_container_' + itemId);
        const row = document.getElementById('row_' + itemId);
        const select = document.getElementById('reason_input_' + itemId);
        const note = document.getElementById('note_input_' + itemId);

        if (checkbox.checked) {
            reasonContainer.style.display = 'block';
            row.classList.add('selected');
            select.disabled = false; 
            note.disabled = false;
        } else {
            reasonContainer.style.display = 'none';
            row.classList.remove('selected');
            select.disabled = true;
            note.disabled = true;
            select.value = ""; 
            note.value = "";
        }
    }

    // --- AXIOS SUBMISSION LOGIC ---
    document.getElementById('returnForm').addEventListener('submit', function(e) {
        e.preventDefault(); 

        const mode = document.getElementById('return_mode').value;
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const url = this.action; 

        let payload = []; 

        if (mode === 'all') {
            // --- GATHER DATA FOR 'ALL' MODE ---
            const globalReason = document.getElementById('global_reason').value;
            const globalNote = document.getElementById('global_note').value;

            if (!globalReason) {
                // Toastr Error
                toastr.error("Please select a reason for returning the entire order.");
                return;
            }

            const checkboxes = document.querySelectorAll('.item-checkbox');
            checkboxes.forEach(cb => {
                payload.push({
                    item_id: cb.value,
                    reason: globalReason,
                    note: globalNote
                });
            });

        } else {
            // --- GATHER DATA FOR 'INDIVIDUAL' MODE ---
            const checkedBoxes = document.querySelectorAll('input[name="selected_items"]:checked');
            
            if (checkedBoxes.length === 0) {
                // Toastr Error
                toastr.error("Please select at least one item to return.");
                return;
            }

            let valid = true;
            checkedBoxes.forEach(cb => {
                const id = cb.value;
                const reason = document.getElementById('reason_input_' + id).value;
                const note = document.getElementById('note_input_' + id).value;

                if (!reason) { valid = false; }

                payload.push({
                    item_id: id,
                    reason: reason,
                    note: note
                });
            });

            if (!valid) {
                // Toastr Error
                toastr.error("Please select a reason for all selected items.");
                return;
            }
        }

        // --- SEND DATA VIA AXIOS ---
        axios.post(url, { returns: payload }, {
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            }
        })
        .then(function (response) {
            // Toastr Success
            toastr.success("Return request submitted successfully.");
            
            // Wait 1.5s for toastr to show, then reload
            setTimeout(function() {
                window.location.reload();
            }, 1500);
        })
        .catch(function (error) {
            console.error('Error:', error);
            
            let errorMessage = "An unexpected error occurred.";
            if (error.response && error.response.data && error.response.data.message) {
                errorMessage = error.response.data.message;
            }
            // Toastr Error
            toastr.error(errorMessage);
        });
    });