const API = "/api";
let token = localStorage.getItem("warehouse_token");
let currentUser = null;
let cart = [];

const $ = (id) => document.getElementById(id);

function authHeaders() {
    return token ? { "Authorization": `Token ${token}`, "Content-Type": "application/json" }
                 : { "Content-Type": "application/json" };
}

async function api(url, options = {}) {
    options.headers = { ...authHeaders(), ...(options.headers || {}) };
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.detail || JSON.stringify(data));
    }
    return data;
}

function showAlert(message, type = "success") {
    $("alertBox").innerHTML =
        `<div class="alert alert-${type}">${message}</div>`;
    setTimeout(() => $("alertBox").innerHTML = "", 4000);
}

async function login(username, password) {
    const data = await api(`${API}/accounts/login/`, {
        method: "POST",
        body: JSON.stringify({ username, password })
    });
    token = data.token;
    currentUser = data.user;
    localStorage.setItem("warehouse_token", token);
    showApp();
}

async function register(username, email, password, role) {
    const data = await api(`${API}/accounts/register/`, {
        method: "POST",
        body: JSON.stringify({ username, email, password, role })
    });
    token = data.token;
    currentUser = data.user;
    localStorage.setItem("warehouse_token", token);
    showApp();
}

async function showApp() {
    $("authSection").classList.add("d-none");
    $("appSection").classList.remove("d-none");
    $("logoutBtn").classList.remove("d-none");
    $("currentUser").textContent = `${currentUser.username} (${currentUser.role})`;

    if (currentUser.role === "WAREHOUSE") {
        $("warehousePanel").classList.remove("d-none");
    }

    await loadWarehouses();
    await searchInventory("");
    await loadRequests();

    if (currentUser.role === "WAREHOUSE") {
        await loadWarehouseRequests();
    }
}

async function loadWarehouses() {
    const warehouses = await api(`${API}/warehouses/`);
    $("warehouseSelect").innerHTML = warehouses.map(w =>
        `<option value="${w.id}">${w.code} - ${w.name} (${w.location})</option>`
    ).join("");
}

async function searchInventory(search) {
    const url = `${API}/inventory/${search ? "?search=" + encodeURIComponent(search) : ""}`;
    const rows = await api(url);

    if (!rows.length) {
        $("inventoryResults").innerHTML = "<p class='text-muted'>No inventory found.</p>";
        return;
    }

    $("inventoryResults").innerHTML = rows.map(row => `
        <div class="material-row">
            <div class="d-flex justify-content-between">
                <div>
                    <strong>${row.material_code} - ${row.material_name}</strong>
                    <div class="text-muted">${row.warehouse_code} - ${row.warehouse_name}</div>
                </div>
                <span class="badge bg-secondary">Available: ${row.quantity}</span>
            </div>
            <div class="input-group mt-2">
                <input id="qty-${row.id}" type="number" min="1" max="${row.quantity}"
                       class="form-control" placeholder="Quantity">
                <button class="btn btn-outline-primary"
                    onclick="addToCart(${row.material}, '${escapeHtml(row.material_name)}', ${row.quantity})">
                    Add
                </button>
            </div>
        </div>
    `).join("");
}

function escapeHtml(value) {
    return value.replace(/[&<>"']/g, ch => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
    }[ch]));
}

async function addToCart(materialId, materialName, available) {
    const warehouseId = Number($("warehouseSelect").value);
    const searchRows = await api(`${API}/inventory/?warehouse=${warehouseId}`);
    const inventory = searchRows.find(x => x.material === materialId);

    if (!inventory) {
        showAlert("This material is not available in the selected warehouse.", "warning");
        return;
    }

    const qty = Number(prompt(`Enter quantity for ${materialName}. Available: ${inventory.quantity}`, "1"));
    if (!Number.isInteger(qty) || qty < 1) return;
    if (qty > inventory.quantity) {
        showAlert(`Only ${inventory.quantity} units are available.`, "warning");
        return;
    }

    const existing = cart.find(x => x.material === materialId);
    if (existing) existing.quantity += qty;
    else cart.push({ material: materialId, name: materialName, quantity: qty });

    renderCart();
}

function renderCart() {
    if (!cart.length) {
        $("cart").innerHTML = "<p class='text-muted'>No materials added.</p>";
        return;
    }

    $("cart").innerHTML = cart.map((item, index) => `
        <div class="cart-item d-flex justify-content-between align-items-center">
            <span><strong>${item.name}</strong> × ${item.quantity}</span>
            <button class="btn btn-sm btn-outline-danger" onclick="removeCart(${index})">Remove</button>
        </div>
    `).join("");
}

function removeCart(index) {
    cart.splice(index, 1);
    renderCart();
}

async function submitRequest() {
    if (!cart.length) {
        showAlert("Add at least one material.", "warning");
        return;
    }

    try {
        await api(`${API}/requests/`, {
            method: "POST",
            body: JSON.stringify({
                warehouse: Number($("warehouseSelect").value),
                notes: $("requestNotes").value,
                items: cart.map(x => ({
                    material: x.material,
                    quantity: x.quantity
                }))
            })
        });

        cart = [];
        $("requestNotes").value = "";
        renderCart();
        await loadRequests();
        showAlert("Material request created successfully.");
    } catch (error) {
        showAlert(error.message, "danger");
    }
}

async function loadRequests() {
    const requests = await api(`${API}/requests/`);

    $("myRequests").innerHTML = requests.map(req => `
        <div class="border rounded p-2 mb-2">
            <div class="d-flex justify-content-between">
                <strong>Request #${req.id}</strong>
                <span class="badge bg-primary status">${req.status}</span>
            </div>
            <div>${req.warehouse_code} - ${req.warehouse_name}</div>
            <small class="text-muted">${new Date(req.requested_at).toLocaleString()}</small>
            <ul class="mb-0 mt-2">
                ${req.items.map(item =>
                    `<li>${item.material_name} × ${item.quantity}</li>`
                ).join("")}
            </ul>
        </div>
    `).join("") || "<p class='text-muted'>No requests.</p>";
}

async function loadWarehouseRequests() {
    const requests = await api(`${API}/requests/`);

    $("warehouseRequests").innerHTML = requests.map(req => `
        <div class="border rounded p-2 mb-2">
            <strong>#${req.id} - ${req.employee_name}</strong>
            <span class="badge bg-secondary">${req.status}</span>
            <div>${req.warehouse_code} - ${req.warehouse_name}</div>
            <ul>
                ${req.items.map(i => `<li>${i.material_name} × ${i.quantity}</li>`).join("")}
            </ul>
            <div class="d-flex gap-1">
                ${req.status === "PENDING"
                    ? `<button class="btn btn-sm btn-success" onclick="changeRequest(${req.id}, 'approve')">Approve</button>
                       <button class="btn btn-sm btn-danger" onclick="changeRequest(${req.id}, 'reject')">Reject</button>`
                    : ""}
                ${["PENDING", "APPROVED"].includes(req.status)
                    ? `<button class="btn btn-sm btn-primary" onclick="changeRequest(${req.id}, 'fulfill')">Fulfill</button>`
                    : ""}
            </div>
        </div>
    `).join("") || "<p class='text-muted'>No requests.</p>";
}

async function changeRequest(id, action) {
    try {
        await api(`${API}/requests/${id}/${action}/`, { method: "POST" });
        await loadRequests();
        await loadWarehouseRequests();
        if (action === "fulfill") await searchInventory($("searchInput").value);
        showAlert(`Request #${id} ${action} successful.`);
    } catch (error) {
        showAlert(error.message, "danger");
    }
}

$("loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
        await login($("loginUsername").value, $("loginPassword").value);
    } catch (error) {
        showAlert(error.message, "danger");
    }
});

$("registerForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
        await register(
            $("regUsername").value,
            $("regEmail").value,
            $("regPassword").value,
            $("regRole").value
        );
    } catch (error) {
        showAlert(error.message, "danger");
    }
});

$("searchBtn").addEventListener("click", () => searchInventory($("searchInput").value));
$("searchInput").addEventListener("keyup", event => {
    if (event.key === "Enter") searchInventory(event.target.value);
});
$("warehouseSelect").addEventListener("change", () => searchInventory($("searchInput").value));
$("submitRequestBtn").addEventListener("click", submitRequest);

$("logoutBtn").addEventListener("click", async () => {
    try {
        await api(`${API}/accounts/logout/`, { method: "POST" });
    } catch (_) {}
    localStorage.removeItem("warehouse_token");
    location.reload();
});

async function start() {
    renderCart();

    if (!token) return;

    try {
        currentUser = await api(`${API}/accounts/me/`);
        showApp();
    } catch (_) {
        localStorage.removeItem("warehouse_token");
        token = null;
    }
}

start();
