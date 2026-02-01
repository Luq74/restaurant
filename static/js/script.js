const tg = window.Telegram.WebApp;
tg.expand();
let keranjang = {};

function filterMenu(category, btn) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.menu-card').forEach(card => {
        card.classList.toggle('show', card.getAttribute('data-category') === category);
    });
}

function tambahItem(nama, harga, btnElement) {
    if (!keranjang[nama]) {
        keranjang[nama] = { harga: harga, qty: 0 };
    }
    keranjang[nama].qty += 1;
    updateUI();
    
    // Update Button UI
    const container = btnElement.closest('.btn-container');
    updateButtonUI(container, nama, harga);
}

function kurangiItem(nama, harga, btnElement) {
    if (keranjang[nama] && keranjang[nama].qty > 0) {
        keranjang[nama].qty -= 1;
        if (keranjang[nama].qty === 0) {
            delete keranjang[nama];
        }
    }
    updateUI();
    
    const container = btnElement.closest('.btn-container');
    updateButtonUI(container, nama, harga);
}

function updateButtonUI(container, nama, harga) {
    const qty = keranjang[nama] ? keranjang[nama].qty : 0;
    
    if (qty > 0) {
        container.innerHTML = `
            <div class="qty-controls" style="display:flex; align-items:center; gap:5px; background:var(--primary-color); border-radius:8px; padding:2px;">
                <button class="qty-btn" onclick="kurangiItem('${nama}', ${harga}, this)" style="background:transparent; color:black; border:none; width:30px; font-weight:bold;">-</button>
                <span class="qty-val" style="color:black; font-weight:bold; min-width:20px; text-align:center;">${qty}</span>
                <button class="qty-btn" onclick="tambahItem('${nama}', ${harga}, this)" style="background:transparent; color:black; border:none; width:30px; font-weight:bold;">+</button>
            </div>
        `;
    } else {
        container.innerHTML = `
            <button class="add-btn" onclick="tambahItem('${nama}', ${harga}, this)">+</button>
        `;
    }
}

function updateUI() {
    const footer = document.getElementById('footerOrder');
    const summary = document.getElementById('totalSummary');
    let totalItem = 0, subtotal = 0;
    for (let item in keranjang) {
        totalItem += keranjang[item].qty;
        subtotal += (keranjang[item].harga * keranjang[item].qty);
    }
    
    if (totalItem > 0) {
        footer.style.display = 'block';
        summary.innerText = `${totalItem} Item | Rp ${subtotal.toLocaleString('id-ID')}`;
    } else {
        footer.style.display = 'none';
    }
}

function bukaPayment() {
    const customerName = document.getElementById('nama').value.trim();
    if (!customerName) {
        showError("Silakan masukkan Nama Pemesan terlebih dahulu!");
        document.getElementById('nama').focus();
        return;
    }

    const modal = document.getElementById('paymentModal');
    const listArea = document.getElementById('orderListSummary');
    let subtotal = 0;
    let html = "";

    const allCards = document.querySelectorAll('.menu-grid .menu-card');

    for (let item in keranjang) {
        const itemData = keranjang[item];
        const itemTotal = itemData.harga * itemData.qty;
        subtotal += itemTotal;

        let catatan = "Tanpa catatan";
        // Find note from input
        allCards.forEach(card => {
            if (card.querySelector('.menu-title').innerText === item) {
                const noteInput = card.querySelector('.note-input');
                if (noteInput && noteInput.value.trim()) {
                    catatan = noteInput.value.trim();
                }
            }
        });
        keranjang[item].currentNote = catatan;

        html += `
        <div class="summary-item">
            <div><b>${item}</b> x${itemData.qty}<br><small style="color:#aaa;">Note: ${catatan}</small></div>
            <div>Rp ${itemTotal.toLocaleString('id-ID')}</div>
        </div>`;
    }

    const tax = subtotal * 0.21;
    const grandTotal = subtotal + tax;

    html += `<div class="summary-item" style="border-top:1px dashed #444; margin-top:10px; padding-top:10px;"><div>Subtotal</div><div>Rp ${subtotal.toLocaleString('id-ID')}</div></div>`;
    html += `<div class="summary-item"><div>Tax & Service (21%)</div><div>Rp ${tax.toLocaleString('id-ID')}</div></div>`;
    
    listArea.innerHTML = html;
    document.getElementById('finalTotalDisplay').innerText = `TOTAL: Rp ${grandTotal.toLocaleString('id-ID')}`;
    
    modal.style.display = 'block';
    document.getElementById('mainContent').style.display = 'none';
    
    // Auto-scroll to top of modal
    modal.scrollTop = 0;
}

function tutupPayment() {
    document.getElementById('paymentModal').style.display = 'none';
    document.getElementById('mainContent').style.display = 'block';
}

function showError(msg) {
    const box = document.getElementById('errorBox');
    box.innerText = msg;
    box.style.display = 'block';
    setTimeout(() => { box.style.display = 'none'; }, 3000);
}

function finalisasiPesanan() {
    const nama = document.getElementById('nama').value;
    const nomorMeja = document.getElementById('nomor-meja').value;

    if (!nama || !nomorMeja) {
        alert('Mohon lengkapi Nama dan Nomor Meja!');
        return;
    }

    if (Object.keys(keranjang).length === 0) {
        alert('Keranjang pesanan masih kosong!');
        return;
    }

    let total = 0;
    const items = {};

    for (const [key, value] of Object.entries(keranjang)) {
        total += value.harga * value.qty;
        items[key] = {
            harga: value.harga,
            qty: value.qty,
            currentNote: value.currentNote || '-'
        };
    }

    const payload = {
        customer: nama,
        table: nomorMeja,
        items: items,
        total: `TOTAL: Rp ${total.toLocaleString('id-ID')}`
    };

    // Show loading state
    const checkoutBtn = document.querySelector('.confirm-pay-btn');
    const originalText = checkoutBtn.innerText;
    checkoutBtn.innerText = 'Mengirim...';
    checkoutBtn.disabled = true;

    // Use Fetch API for both Telegram and Browser
    fetch('/submit_order', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server Error: ${response.status} (URL: ${response.url})`);
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'ok') {
            alert('✅ Pesanan Berhasil Terkirim!');
            
            // If in Telegram, try to close
            if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) {
                window.Telegram.WebApp.close();
            } else {
                // Reset UI for Browser
                keranjang = {};
                updateUI();
                document.getElementById('nama').value = '';
                document.getElementById('nomor-meja').value = '';
                tutupPayment(); // Close modal
            }
        } else {
            alert('⚠️ Gagal mengirim pesanan: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Order Error:', error);
        alert('❌ Gagal mengirim pesanan. Pastikan server berjalan.\nDetail: ' + error.message);
    })
    .finally(() => {
        checkoutBtn.innerText = originalText;
        checkoutBtn.disabled = false;
    });
}

// Image Zoom Functions
function zoomImage(src) {
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('zoomedImage');
    modal.style.display = "block";
    modalImg.src = src;
}

function closeZoom() {
    document.getElementById('imageModal').style.display = "none";
}

// Call Waiter Function (Browser & Telegram Compatible)
function panggilWaiter() {
    const nama = document.getElementById('nama').value.trim() || 'Tamu';
    const nomorMeja = document.getElementById('nomor-meja').value.trim();
    
    if (!nomorMeja) {
        showError("Mohon isi Nomor Meja agar pelayan tahu posisi Anda!");
        document.getElementById('nomor-meja').focus();
        return;
    }

    if(!confirm(`Panggil pelayan ke Meja ${nomorMeja}?`)) return;

    fetch('/call_waiter', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ nama: nama, table_number: nomorMeja })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server Error: ${response.status} ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'ok') {
            alert('✅ Pelayan telah dipanggil. Mohon tunggu sebentar.');
        } else {
            alert('⚠️ Gagal memanggil pelayan: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Waiter Error:', error);
        alert('❌ Gagal memanggil pelayan. Pastikan server berjalan.\nDetail: ' + error.message);
    });
}
