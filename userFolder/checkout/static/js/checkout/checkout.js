document.addEventListener('DOMContentLoaded', function() {
    // --- 1. SELECTION LOGIC (Visual Blue Border) ---
    const selectionCards = document.querySelectorAll('.selection-card');

    selectionCards.forEach(card => {
        card.addEventListener('click', function(e) {
            // If clicking edit link or clicking inside modal triggers, ignore
            if (e.target.closest('.edit-btn')) return;
            // If clicking the add new trigger, open modal (handled separately)
            if (e.target.closest('#addNewAddressBtn') || this.classList.contains('add-new-trigger')) return;

            const radio = this.querySelector('input[type="radio"]');
            if (radio) {
                const groupName = radio.name;
                // Unselect others in same group (if any)
                document.querySelectorAll(`input[name="${groupName}"]`).forEach(input => {
                    const parentCard = input.closest('.selection-card');
                    if (parentCard) parentCard.classList.remove('selected');
                });

                // Select this one
                radio.checked = true;
                this.classList.add('selected');
            }
        });

        // Also allow clicking the internal radio to propagate visual selection
        const innerRadio = card.querySelector('input[type="radio"]');
        if (innerRadio) {
            innerRadio.addEventListener('change', function() {
                if (!this.checked) return;
                const groupName = this.name;
                document.querySelectorAll(`input[name="${groupName}"]`).forEach(input => {
                    const parentCard = input.closest('.selection-card');
                    if (parentCard) parentCard.classList.remove('selected');
                });
                const parent = this.closest('.selection-card');
                if (parent) parent.classList.add('selected');
            });
        }
    });

    // --- 2. MODAL LOGIC (Add & Edit) ---
    const modal = document.getElementById('addressModal');
    const addBtn = document.getElementById('addNewAddressBtn');
    const closeBtn = document.getElementById('closeAddressModalBtn');
    const cancelBtn = document.getElementById('cancelAddressBtn');
    const addressForm = document.getElementById('addressForm');
    const modalTitle = document.getElementById('addressModalTitle');
    const fetchUrlBaseElem = document.getElementById('fetchUrlBase');
    const fetchUrlBase = fetchUrlBaseElem ? fetchUrlBaseElem.dataset.urlBase : '';

    function openModal() {
        if (!modal) return;
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
        // focus first input for accessibility
        const firstInput = modal.querySelector('input, textarea, select, button');
        if (firstInput) firstInput.focus();
    }

    function closeModal() {
        if (!modal) return;
        modal.classList.remove('active');
        modal.setAttribute('aria-hidden', 'true');
    }

    // Open Modal for ADD
    if (addBtn) {
        addBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (addressForm) addressForm.reset();
            const hiddenId = document.getElementById('address_id');
            if (hiddenId) hiddenId.value = '';
            // clear custom radio visuals
            const radios = document.querySelectorAll('.radio-icon-container input');
            radios.forEach(r => r.checked = false);
            modalTitle.innerText = "Add New Address";
            openModal();
        });

        // keyboard support
        addBtn.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                addBtn.click();
            }
        });
    }

    // Open Modal for EDIT (fetch address data)
    document.querySelectorAll('.edit-address-trigger').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const addressId = this.dataset.id;
            if (!addressId || !fetchUrlBase) return;

            // Safely replace the placeholder __ADDR_ID__ in the url template
            const url = fetchUrlBase.replace('__ADDR_ID__', encodeURIComponent(addressId));

            fetch(url, { credentials: 'same-origin' })
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.json();
                })
                .then(data => {
                    if (data && data.status === 'success') {
                        const addr = data.address;

                        // Populate Fields (guarded)
                        const setIf = (id, val) => {
                            const el = document.getElementById(id);
                            if (el) el.value = val ?? '';
                        };

                        setIf('address_id', addr.id);
                        setIf('full_name', addr.full_name);
                        setIf('address_line_1', addr.address_line_1);
                        setIf('address_line_2', addr.address_line_2);
                        setIf('city', addr.city);
                        setIf('state', addr.state);
                        setIf('postal_code', addr.postal_code);
                        setIf('phone_number', addr.phone_number);
                        setIf('country', addr.country);

                        // Address type radio
                        if (addr.address_type) {
                            const typeRadio = document.querySelector(`input[name="address_type"][value="${addr.address_type}"]`);
                            if (typeRadio) typeRadio.checked = true;
                        }

                        // Checkbox
                        const isDefaultEl = document.getElementById('is_default');
                        if (isDefaultEl) isDefaultEl.checked = !!addr.is_default;

                        modalTitle.innerText = "Edit Address";
                        openModal();
                    } else {
                        console.error('Failed to fetch address:', data);
                    }
                })
                .catch(err => console.error("Error fetching address:", err));
        });
    });

    // Close Modal (buttons + backdrop)
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

    window.addEventListener('click', function(e) {
        if (!modal) return;
        if (e.target === modal) closeModal();
    });

    // Escape key closes modal
    window.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            if (modal && modal.classList.contains('active')) closeModal();
        }
    });
});
