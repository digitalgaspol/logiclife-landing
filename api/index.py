from flask import Flask, render_template_string, request, redirect, session, url_for, jsonify
import hashlib
import requests
import random
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
app.secret_key = 'rahasia_negara_bos_nexa'

# ==============================================================================
# ⚙️ KONFIGURASI DUITKU & ADMIN
# ==============================================================================
MERCHANT_CODE = "DS28030"      
API_KEY = "58191656b8692a368c766a9ca4124ee0"      
SANDBOX_URL = "https://sandbox.duitku.com/webapi/api/merchant/v2/inquiry"
PAYMENT_METHOD = "SP" # QRIS ShopeePay Sandbox

ADMIN_PIN = "M3isy4851" # PIN Admin Bos

# ==============================================================================
# 🔥 INIT FIREBASE
# ==============================================================================
db = None
try:
    if not firebase_admin._apps:
        cred_json = os.environ.get('FIREBASE_CREDENTIALS')
        if cred_json:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
    else:
        db = firestore.client()
except Exception as e:
    print(f"Firebase Error: {e}")

# ==============================================================================
# 🌐 1. HALAMAN PUBLIK (LANDING PAGE)
# ==============================================================================
@app.route('/')
def home():
    products_data = []
    contact_data = {
        "company": "PT. LogicLife Digital",
        "address": "Indonesia",
        "whatsapp": "628123456789",
        "email": "support@logiclife.site"
    }

    if db:
        # Load Produk
        docs = db.collection('products').stream()
        for doc in docs:
            prod = doc.to_dict()
            prod['id'] = doc.id
            products_data.append(prod)
        
        # Load Kontak
        settings_doc = db.collection('settings').document('contact').get()
        if settings_doc.exists:
            db_contact = settings_doc.to_dict()
            contact_data.update(db_contact)
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LogicLife - Digital Ecosystem</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Outfit', sans-serif; }
            .glass { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.5); }
        </style>
    </head>
    <body class="bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 text-slate-800 min-h-screen relative">
        <nav class="glass sticky top-0 z-50">
            <div class="container mx-auto px-6 h-16 flex justify-between items-center">
                <span class="text-xl font-extrabold text-slate-900">LogicLife<span class="text-indigo-600">.</span></span>
                <div class="flex gap-6">
                    <a href="#products" class="text-sm font-bold text-slate-600 hover:text-indigo-600">Produk</a>
                    <a href="/admin" class="text-sm font-medium text-slate-500 hover:text-slate-900">Login Admin</a>
                </div>
            </div>
        </nav>

        <header class="pt-24 pb-20 px-6 text-center">
            <h1 class="text-5xl md:text-7xl font-extrabold text-slate-900 mb-6">Solusi Digital <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">Tanpa Batas</span></h1>
            <p class="text-lg text-slate-600 mb-8">Ekosistem aplikasi untuk produktivitas bisnis dan personal Anda.</p>
            <a href="#products" class="bg-slate-900 text-white px-8 py-3 rounded-full font-bold shadow-xl hover:bg-slate-800 transition">Lihat Produk</a>
        </header>

        <section id="products" class="container mx-auto px-6 py-10 mb-20">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
                {% for item in products %}
                <div class="glass bg-white/80 rounded-3xl shadow-xl overflow-hidden flex flex-col hover:-translate-y-2 transition duration-300">
                    <div class="h-64 w-full bg-white relative overflow-hidden p-4 flex items-center justify-center">
                        <img src="{{ item.image_url }}" class="w-full h-full object-contain" onerror="this.src='https://placehold.co/600x400?text=No+Image'">
                    </div>
                    <div class="p-8 flex-grow flex flex-col bg-white/50">
                        <h2 class="text-2xl font-extrabold mb-1">{{ item.name }}</h2>
                        <p class="text-indigo-600 text-sm font-bold mb-4">{{ item.tagline }}</p>
                        <p class="text-slate-500 text-sm mb-6">{{ item.description }}</p>
                        
                        <div class="mt-auto pt-6 border-t border-slate-100">
                            <div class="flex justify-between items-center mb-4">
                                <span class="text-3xl font-extrabold">Rp {{ "{:,.0f}".format(item.price).replace(',', '.') }}</span>
                                <span class="text-xs line-through text-slate-400 bg-slate-100 px-2 py-1 rounded">Rp {{ item.original_price }}</span>
                            </div>
                            <form action="/checkout" method="POST">
                                <input type="hidden" name="product_id" value="{{ item.id }}">
                                <button class="w-full bg-slate-900 text-white font-bold py-3 rounded-xl hover:bg-indigo-600 transition shadow-lg">BELI LISENSI</button>
                            </form>
                        </div>
                    </div>
                </div>
                {% else %}
                <div class="col-span-3 text-center py-20 text-slate-400">Belum ada produk. Silakan tambah di Admin.</div>
                {% endfor %}
            </div>
        </section>
        
        <footer class="bg-slate-900 text-slate-300 py-10 text-center">
            <p class="font-bold text-white text-xl mb-2">{{ contact.company }}</p>
            <p class="mb-4">{{ contact.address }}</p>
            <p class="text-xs text-slate-500">&copy; 2026 LogicLife Ecosystem.</p>
        </footer>
    </body>
    </html>
    ''', products=products_data, contact=contact_data)

# ==============================================================================
# 💰 2. API PRICING (MULTI-APP SUPPORT)
# ==============================================================================
@app.route('/api/get_pricing')
def get_pricing():
    app_id = request.args.get('app_id') # nexapos atau moodly
    price = 150000 # Default fallback
    
    if db:
        doc = db.collection('settings').document('pricing').get()
        if doc.exists:
            data = doc.to_dict()
            # 👇 PILIH HARGA SESUAI ID APLIKASI
            if app_id == 'moodly':
                price = data.get('moodly_price', 50000)
            else:
                price = data.get('nexapos_price', 150000) # Default NexaPOS
    
    return jsonify({
        "app_id": app_id,
        "price": price,
        "formatted": "{:,.0f}".format(price).replace(',', '.')
    })

# ==============================================================================
# 🛒 3. PROSES BAYAR "PRO LIFETIME" (MULTI-APP)
# ==============================================================================
@app.route('/buy_pro')
def buy_pro():
    uid = request.args.get('uid')
    email = request.args.get('email')
    app_id = request.args.get('app_id') # 👇 Diterima dari Aplikasi
    
    if not uid: return "Error: User ID tidak ditemukan."

    # A. TENTUKAN HARGA & NAMA PRODUK
    product_price = 150000
    product_name = "NexaPOS PRO Lifetime"

    if db:
        doc = db.collection('settings').document('pricing').get()
        if doc.exists:
            data = doc.to_dict()
            if app_id == 'moodly':
                product_price = int(data.get('moodly_price', 50000))
                product_name = "Moodly Premium"
            else:
                product_price = int(data.get('nexapos_price', 150000))
                product_name = "NexaPOS PRO Lifetime"

    # B. BUAT ORDER ID UNIK (Format: PRO-APPID-UID-ACAK)
    order_id = f"PRO-{app_id}-{uid}-{random.randint(100,999)}"
    
    # C. HITUNG SIGNATURE DUITKU
    signature_str = MERCHANT_CODE + order_id + str(product_price) + API_KEY
    signature = hashlib.md5(signature_str.encode('utf-8')).hexdigest()

    # D. KIRIM KE DUITKU
    payload = {
        "merchantCode": MERCHANT_CODE,
        "paymentAmount": product_price,
        "merchantOrderId": order_id,
        "productDetails": product_name,
        "email": email,
        "paymentMethod": PAYMENT_METHOD,
        "callbackUrl": "https://logiclife.site/callback_pro",
        "returnUrl": "https://logiclife.site/success_pro",
        "signature": signature,
        "expiryPeriod": 60
    }

    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SANDBOX_URL, json=payload, headers=headers)
        data = response.json()
        if 'paymentUrl' in data: return redirect(data['paymentUrl'])
        return f"Error Duitku: {data}"
    except Exception as e: return str(e)

@app.route('/callback_pro', methods=['POST'])
def callback_pro():
    data = request.form
    merchantOrderId = data.get('merchantOrderId') 
    resultCode = data.get('resultCode')

    if resultCode == '00': # Pembayaran Sukses
        # Format Order ID: PRO-nexapos-UIDUser-123
        parts = merchantOrderId.split('-')
        if len(parts) >= 3:
            app_id = parts[1] # nexapos atau moodly
            uid = parts[2]
            
            if db:
                # Update Status Sesuai Aplikasi
                field_to_update = 'is_pro' # Default NexaPOS
                if app_id == 'moodly':
                    field_to_update = 'is_pro_moodly'

                db.collection('users').document(uid).set({
                    field_to_update: True,
                    f'{field_to_update}_since': firestore.SERVER_TIMESTAMP
                }, merge=True)
                
    return "OK"

@app.route('/success_pro')
def success_pro():
    return "<h1>Pembayaran Berhasil! Silakan kembali ke Aplikasi.</h1>"

# ==============================================================================
# 🛒 4. CHECKOUT PRODUK BIASA (EBOOK/COURSE)
# ==============================================================================
@app.route('/checkout', methods=['POST'])
def checkout():
    product_id = request.form.get('product_id')
    product = None
    if db:
        doc = db.collection('products').document(product_id).get()
        if doc.exists: product = doc.to_dict()
    if not product: return "Error: Produk tidak ditemukan."
    
    amount = int(product['price'])
    product_name = product['name']
    order_id = product['prefix'] + str(random.randint(10000, 99999))
    
    signature_str = MERCHANT_CODE + order_id + str(amount) + API_KEY
    signature = hashlib.md5(signature_str.encode('utf-8')).hexdigest()
    
    payload = {
        "merchantCode": MERCHANT_CODE,
        "paymentAmount": amount,
        "merchantOrderId": order_id,
        "productDetails": product_name,
        "email": "customer@example.com",
        "paymentMethod": PAYMENT_METHOD,
        "callbackUrl": "https://logiclife.site/callback",
        "returnUrl": "https://logiclife.site/finish",
        "signature": signature,
        "expiryPeriod": 60
    }
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SANDBOX_URL, json=payload, headers=headers)
        data = response.json()
        if 'paymentUrl' in data: return redirect(data['paymentUrl'])
        return f"Error Duitku: {data}"
    except Exception as e: return str(e)

@app.route('/callback', methods=['POST'])
def callback():
    return "OK"

@app.route('/finish')
def finish():
    return "<h1>Transaksi Selesai! Terima kasih.</h1>"

# ==============================================================================
# 🔐 5. ADMIN PANEL (LENGKAP: CRUD + SETTING 2 HARGA)
# ==============================================================================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # A. LOGIC LOGIN
    if request.method == 'POST':
        if request.form.get('pin') == ADMIN_PIN:
            session['is_admin'] = True
            return redirect('/admin')
        else: return "PIN SALAH!"

    if not session.get('is_admin'):
        return render_template_string('<form method="POST" style="text-align:center;padding:50px;font-family:sans-serif;"><h2>Admin Login</h2><input type="password" name="pin" placeholder="PIN Rahasia" style="padding:10px;"><br><br><button style="padding:10px 20px;">Masuk</button></form>')

    # B. LOAD DATA
    products_data = []
    contact_data = {"company": "", "address": "", "whatsapp": "", "email": ""}
    pricing_data = {"nexapos_price": 150000, "moodly_price": 50000} # Default

    if db:
        # Load Produk
        docs = db.collection('products').stream()
        for doc in docs:
            prod = doc.to_dict()
            prod['id'] = doc.id
            products_data.append(prod)
        
        # Load Kontak
        settings_doc = db.collection('settings').document('contact').get()
        if settings_doc.exists: contact_data = settings_doc.to_dict()

        # Load Harga (Multi-App)
        price_doc = db.collection('settings').document('pricing').get()
        if price_doc.exists: pricing_data = price_doc.to_dict()

    # C. RENDER ADMIN DASHBOARD
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="id">
    <head><title>Admin LogicLife</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 p-10 font-sans">
        <div class="max-w-6xl mx-auto">
            <div class="flex justify-between items-center mb-8 bg-white p-4 rounded-xl shadow-sm">
                <h1 class="text-2xl font-bold text-slate-800">⚙️ Admin Dashboard</h1>
                <div class="gap-2 flex">
                    <a href="/" class="bg-slate-800 text-white px-5 py-2 rounded-lg hover:bg-slate-900 font-bold text-sm">🏠 Web Utama</a>
                    <a href="/logout" class="bg-red-500 text-white px-5 py-2 rounded-lg hover:bg-red-600 font-bold text-sm">🚪 Keluar</a>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
                <div class="bg-white p-8 rounded-xl shadow-md border-t-4 border-emerald-500 h-fit">
                    <h2 class="text-xl font-bold mb-6 text-emerald-900">💰 Setting Harga Aplikasi</h2>
                    <form action="/admin/settings" method="POST" class="grid gap-4">
                        <div class="grid grid-cols-2 gap-4">
                            <div class="bg-indigo-50 p-3 rounded-lg border border-indigo-200">
                                <label class="block text-xs font-bold text-indigo-800 uppercase mb-1">NexaPOS PRO</label>
                                <div class="flex items-center gap-1">
                                    <span class="font-bold text-slate-500 text-sm">Rp</span>
                                    <input type="number" name="nexapos_price" value="{{ pricing.nexapos_price }}" class="w-full border bg-white p-1 rounded font-bold" required>
                                </div>
                            </div>
                            <div class="bg-pink-50 p-3 rounded-lg border border-pink-200">
                                <label class="block text-xs font-bold text-pink-800 uppercase mb-1">Moodly Premium</label>
                                <div class="flex items-center gap-1">
                                    <span class="font-bold text-slate-500 text-sm">Rp</span>
                                    <input type="number" name="moodly_price" value="{{ pricing.moodly_price }}" class="w-full border bg-white p-1 rounded font-bold" required>
                                </div>
                            </div>
                        </div>
                        <hr class="border-slate-200 my-2">
                        <h2 class="text-sm font-bold text-slate-500 uppercase">Kontak Perusahaan</h2>
                        <input type="text" name="company" value="{{ contact.company }}" placeholder="Nama PT" class="w-full border bg-slate-50 p-2 rounded" required>
                        <input type="text" name="address" value="{{ contact.address }}" placeholder="Alamat" class="w-full border bg-slate-50 p-2 rounded" required>
                        <input type="number" name="whatsapp" value="{{ contact.whatsapp }}" placeholder="No WA (62...)" class="w-full border bg-slate-50 p-2 rounded" required>
                        <input type="email" name="email" value="{{ contact.email }}" placeholder="Email" class="w-full border bg-slate-50 p-2 rounded" required>
                        
                        <button class="bg-emerald-600 text-white w-full py-3 rounded-lg font-bold hover:bg-emerald-700 shadow-lg mt-2">💾 SIMPAN SEMUA</button>
                    </form>
                </div>

                <div class="bg-white p-8 rounded-xl shadow-md border-t-4 border-indigo-600">
                    <h2 class="text-xl font-bold mb-6 text-indigo-900">📦 Tambah Produk Digital</h2>
                    <form action="/admin/add" method="POST" class="grid gap-3">
                        <input type="text" name="name" placeholder="Nama Produk (Misal: Ebook Viral)" class="w-full border bg-slate-50 p-2 rounded" required>
                        <input type="text" name="tagline" placeholder="Tagline Pendek" class="w-full border bg-slate-50 p-2 rounded" required>
                        <div class="grid grid-cols-2 gap-2">
                            <input type="number" name="price" placeholder="Harga Jual" class="w-full border bg-slate-50 p-2 rounded" required>
                            <input type="text" name="original_price" placeholder="Harga Coret" class="w-full border bg-slate-50 p-2 rounded" required>
                        </div>
                        <input type="text" name="prefix" placeholder="Prefix Order (Contoh: BOOK-)" class="w-full border bg-slate-50 p-2 rounded" required>
                        <input type="text" name="image_url" placeholder="Link Gambar (https://...)" class="w-full border bg-slate-50 p-2 rounded" required>
                        <input type="text" name="download_url" placeholder="Link Download File" class="w-full border bg-slate-50 p-2 rounded">
                        <textarea name="description" placeholder="Deskripsi Produk..." class="w-full border bg-slate-50 p-2 rounded" rows="3" required></textarea>
                        <button class="bg-indigo-600 text-white w-full py-3 rounded-lg font-bold hover:bg-indigo-700 shadow-lg mt-2">+ UPLOAD PRODUK</button>
                    </form>
                </div>
            </div>

            <div class="bg-white p-8 rounded-xl shadow-sm border border-slate-200">
                <h2 class="text-xl font-bold mb-6 text-slate-700">📋 Daftar Produk Aktif</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {% for item in products %}
                    <div class="border border-slate-200 p-4 rounded-lg flex gap-4 items-start relative group hover:bg-slate-50 transition">
                        <img src="{{ item.image_url }}" class="w-16 h-16 object-contain bg-white rounded border">
                        <div>
                            <h3 class="font-bold text-slate-800">{{ item.name }}</h3>
                            <p class="text-xs font-bold text-emerald-600">Rp {{ item.price }}</p>
                            <p class="text-xs text-slate-400 mt-1">{{ item.prefix }}...</p>
                        </div>
                        <div class="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition">
                            <a href="/admin/edit/{{ item.id }}" class="bg-yellow-100 text-yellow-700 p-2 rounded hover:bg-yellow-200 text-xs">✏️</a>
                            <a href="/admin/delete/{{ item.id }}" onclick="return confirm('Hapus?')" class="bg-red-100 text-red-700 p-2 rounded hover:bg-red-200 text-xs">🗑️</a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </body>
    </html>
    ''', products=products_data, contact=contact_data, pricing=pricing_data)

# ==============================================================================
# ⚙️ 6. ROUTE CRUD ADMIN (PRODUK & SETTING)
# ==============================================================================
@app.route('/admin/settings', methods=['POST'])
def update_settings():
    if not session.get('is_admin'): return redirect('/admin')
    
    # Update Kontak
    contact_data = {
        "company": request.form.get('company'), 
        "address": request.form.get('address'), 
        "whatsapp": request.form.get('whatsapp'), 
        "email": request.form.get('email').strip()
    }
    if db: db.collection('settings').document('contact').set(contact_data)

    # Update Harga Multi-App
    nexapos_price = request.form.get('nexapos_price')
    moodly_price = request.form.get('moodly_price')
    if db:
        db.collection('settings').document('pricing').set({
            'nexapos_price': int(nexapos_price),
            'moodly_price': int(moodly_price)
        }, merge=True)

    return redirect('/admin')

@app.route('/admin/add', methods=['POST'])
def add_product():
    if not session.get('is_admin'): return redirect('/admin')
    data = { "name": request.form.get('name'), "tagline": request.form.get('tagline'), "price": int(request.form.get('price')), "original_price": request.form.get('original_price'), "prefix": request.form.get('prefix'), "description": request.form.get('description'), "image_url": request.form.get('image_url'), "download_url": request.form.get('download_url'), "created_at": firestore.SERVER_TIMESTAMP }
    if db: db.collection('products').add(data)
    return redirect('/admin')

@app.route('/admin/delete/<id>')
def delete_product(id):
    if not session.get('is_admin'): return redirect('/admin')
    if db: db.collection('products').document(id).delete()
    return redirect('/admin')

@app.route('/admin/edit/<id>')
def edit_product_page(id):
    if not session.get('is_admin'): return redirect('/admin')
    product = {}
    if db:
        doc = db.collection('products').document(id).get()
        if doc.exists:
            product = doc.to_dict()
            product['id'] = doc.id
    return render_template_string('''<!DOCTYPE html><html lang="id"><head><title>Edit</title><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-slate-100 p-10 flex justify-center"><div class="bg-white p-8 rounded-xl shadow w-full max-w-md"><h2 class="font-bold text-xl mb-4">Edit Produk</h2><form action="/admin/update/{{ product.id }}" method="POST" class="grid gap-3"><input type="text" name="name" value="{{ product.name }}" class="border p-2 w-full rounded"><input type="number" name="price" value="{{ product.price }}" class="border p-2 w-full rounded"><textarea name="description" class="border p-2 w-full rounded">{{ product.description }}</textarea><button class="bg-indigo-600 text-white w-full py-2 rounded font-bold">UPDATE</button><a href="/admin" class="block text-center mt-2 text-slate-500">Batal</a></form></div></body></html>''', product=product)

@app.route('/admin/update/<id>', methods=['POST'])
def update_product_logic(id):
    if not session.get('is_admin'): return redirect('/admin')
    data = { "name": request.form.get('name'), "price": int(request.form.get('price')), "description": request.form.get('description') }
    if db: db.collection('products').document(id).update(data)
    return redirect('/admin')

@app.route('/logout')
def logout(): session.pop('is_admin', None); return redirect('/')