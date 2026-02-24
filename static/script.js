// ============================
// Toggle Password Visibility
// ============================
function togglePassword(id, btn) {
    const input = document.getElementById(id);

    if (input.type === "password") {
        input.type = "text";
        btn.innerText = "Hide";
    } else {
        input.type = "password";
        btn.innerText = "Show";
    }
}

// ============================
// Toggle Closure Reason Visibility
// ============================
function toggleClosureReason(ticketId) {
    const statusSelect = document.getElementById("status-" + ticketId);
    const closureSection = document.getElementById("closure-section-" + ticketId);

    if (!statusSelect || !closureSection) return;

    if (statusSelect.value === "Closed") {
        closureSection.classList.remove("hidden");
    } else {
        closureSection.classList.add("hidden");
    }
}

// ============================
// Toggle "Other" Textarea
// ============================
function toggleOtherReason(ticketId) {
    const reasonSelect = document.getElementById("closure-" + ticketId);
    const otherBox = document.getElementById("other-reason-" + ticketId);

    if (!reasonSelect || !otherBox) return;

    if (reasonSelect.value === "Other") {
        otherBox.classList.remove("hidden");
    } else {
        otherBox.classList.add("hidden");
    }
}

// ============================
// Dashboard Charts
// ============================

document.addEventListener("DOMContentLoaded", function () {

    // Prevent errors if Chart.js is not loaded
    if (typeof Chart === "undefined") return;

    // ========================
    // Status Chart
    // ========================
    const statusDataElement = document.getElementById("status-data");
    const statusCanvas = document.getElementById("statusChart");

    if (statusDataElement && statusCanvas) {

        const statusData = JSON.parse(statusDataElement.textContent);

        const labels = statusData.map(item => item.status);
        const counts = statusData.map(item => item.count);

        new Chart(statusCanvas, {
            type: "pie",
            data: {
                labels: labels,
                datasets: [{
                    data: counts,
                    backgroundColor: [
                        "#6366F1",
                        "#10B981",
                        "#F59E0B",
                        "#EF4444",
                        "#3B82F6",
                        "#8B5CF6"
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: "bottom"
                    }
                }
            }
        });
    }

    // ========================
    // Department Chart
    // ========================
    const deptDataElement = document.getElementById("department-data");
    const deptCanvas = document.getElementById("departmentChart");

    if (deptDataElement && deptCanvas) {

        const deptData = JSON.parse(deptDataElement.textContent);

        const labels = deptData.map(item => item.department);
        const counts = deptData.map(item => item.count);

        new Chart(deptCanvas, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Tickets",
                    data: counts,
                    backgroundColor: "#6366F1"
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

});