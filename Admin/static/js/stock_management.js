document.addEventListener('DOMContentLoaded', function() {
    
    // Find all expandable product rows
    const expandableRows = document.querySelectorAll('.product-row.expandable');

    expandableRows.forEach(row => {
        row.addEventListener('click', function() {
            // Get the target ID from the data-target attribute
            const targetId = this.dataset.target;
            
            // Find all variant rows that belong to this product
            const variantRows = document.querySelectorAll(`.variant-row[data-parent="${targetId}"]`);
            
            // Find the icon in this row
            const icon = this.querySelector('.toggle-icon');

            // Toggle visibility for each variant row
            variantRows.forEach(vRow => {
                vRow.classList.toggle('hidden');
            });

            // Toggle the icon class
            if (icon.classList.contains('fa-chevron-right')) {
                icon.classList.remove('fa-chevron-right');
                icon.classList.add('fa-chevron-down');
            } else {
                icon.classList.remove('fa-chevron-down');
                icon.classList.add('fa-chevron-right');
            }
        });
    });

});