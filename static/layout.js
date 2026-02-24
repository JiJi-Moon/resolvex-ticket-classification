function toggleUserMenu() {
    const menu = document.getElementById("userDropdown");
    const notifMenu = document.getElementById("notificationDropdown");

    // Close notifications if open
    if (notifMenu) notifMenu.classList.add("hidden");

    if (menu) {
        menu.classList.toggle("hidden");
    }
}

function toggleNotifications() {
    const dropdown = document.getElementById("notificationDropdown");
    const userMenu = document.getElementById("userDropdown");

    // Close user menu if open
    if (userMenu) userMenu.classList.add("hidden");

    if (dropdown) {
        dropdown.classList.toggle("hidden");
    }
}

// Close dropdowns if clicked outside
window.onclick = function (event) {
    if (!event.target.closest(".user-menu-container")) {
        const userMenu = document.getElementById("userDropdown");
        const notifMenu = document.getElementById("notificationDropdown");

        if (userMenu) userMenu.classList.add("hidden");
        if (notifMenu) notifMenu.classList.add("hidden");
    }
};
