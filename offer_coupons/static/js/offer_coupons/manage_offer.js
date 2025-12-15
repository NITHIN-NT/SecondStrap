document.addEventListener("DOMContentLoaded", function () {
    const targetType = document.getElementById("targetType");

    const categorySection = document.getElementById("categorySection");
    const productSection = document.getElementById("productSection");
    const orderSection = document.getElementById("orderSection");

    function toggleTargetSections() {
        categorySection.style.display = "none";
        productSection.style.display = "none";
        orderSection.style.display = "none";

        if (targetType.value === "category") {
            categorySection.style.display = "block";
        }

        if (targetType.value === "product") {
            productSection.style.display = "block";
        }

        if (targetType.value === "order") {
            orderSection.style.display = "block";
        }
    }

    targetType.addEventListener("change", toggleTargetSections);
    toggleTargetSections();
});
