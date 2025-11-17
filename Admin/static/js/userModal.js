// Wait for the DOM to be fully loaded before running the script
document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. Get all DOM elements ---
    const modal = document.getElementById('confirmation-modal');
    if (!modal) return; // Stop if modal isn't on the page

    const modalContent = modal.querySelector('.modal-content');
    const modalTitle = document.getElementById('modal-title');
    const modalMessage = document.getElementById('modal-message');
    const modalIconContainer = document.getElementById('modal-icon-container');
    const modalIcon = document.getElementById('modal-icon');
    const confirmBtn = document.getElementById('modal-confirm-btn');
    const cancelBtn = document.getElementById('modal-cancel-btn');
    const closeBtn = document.getElementById('modal-close-btn');
    
    // Get all buttons that should open the modal
    const triggerButtons = document.querySelectorAll('.modal-trigger');

    // This config object mirrors your React component's logic
    const modalConfig = {
        delete: {
            icon: 'fa-solid fa-trash-can',
            iconContainerClass: 'modal-type-delete',
            confirmText: 'Delete',
            title: 'Delete User?',
        },
        block: {
            icon: 'fa-solid fa-ban',
            iconContainerClass: 'modal-type-block',
            confirmText: 'Block',
            title: 'Block User?',
        },
        unblock: {
            icon: 'fa-solid fa-shield-check',
            iconContainerClass: 'modal-type-unblock',
            confirmText: 'Unblock',
            title: 'Unblock User?',
        },
    };

    // --- 2. Define functions ---

    /**
     * Opens the modal and configures it based on the action type.
     * @param {string} type - 'block', 'unblock', or 'delete'
     * @param {string} username - The user's name
     * @param {string} url - The URL to navigate to on confirm
     */
    function openModal(type, username, url) {
        const config = modalConfig[type];
        if (!config) return;

        // Reset classes
        modal.className = 'modal-backdrop';
        modal.classList.add(config.iconContainerClass);
        
        // Set icon
        modalIcon.className = config.icon;
        
        // Set text
        modalTitle.textContent = config.title;
        modalMessage.textContent = `Are you sure you want to ${type} ${username}? This action can be undone.`;
        confirmBtn.textContent = config.confirmText;
        
        // Store the URL on the confirm button
        confirmBtn.dataset.url = url;

        // Show the modal
        modal.style.display = 'flex';
    }

    /**
     * Closes the modal.
     */
    function closeModal() {
        modal.style.display = 'none';
        // Clear the URL to be safe
        confirmBtn.dataset.url = ''; 
    }

    // --- 3. Add event listeners ---

    // Listen for clicks on all trigger buttons
    triggerButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const type = button.dataset.type;
            const username = button.dataset.username;
            const url = button.dataset.url;
            
            openModal(type, username, url);
        });
    });

    // Confirm button click
    confirmBtn.addEventListener('click', () => {
        const url = confirmBtn.dataset.url;
        if (url) {
            // This is what performs the block/unblock action
            window.location.href = url;
        }
    });

    // Close modal listeners
    cancelBtn.addEventListener('click', closeModal);
    closeBtn.addEventListener('click', closeModal);
    
    // Close modal if backdrop is clicked
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Close modal on 'Escape' key press (like in your React component)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            closeModal();
        }
    });
});