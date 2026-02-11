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
# 🌐 1. HALAMAN PUBLIK (HOME DENGAN TOMBOL KEREN)
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
        docs = db.collection('products').stream()
        for doc in docs:
            prod = doc.to_dict()
            prod['id'] = doc.id
            products_data.append(prod)
        
        settings_doc = db.collection('settings').document('contact').get()
        if settings_doc.exists:
            contact_data.update(settings_doc.to_dict())
    
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
            .prose ul { list-style-type: disc; padding-left: 20px; margin-bottom: 10px; }
            .prose ol { list-style-type: decimal; padding-left: 20px; margin-bottom: 10px; }
            .prose p { margin-bottom: 10px; }
            .prose strong { font-weight: 800; color: #4338ca; }
        </style>
    </head>
    <body class="bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 text-slate-800 min-h-screen relative">
        <nav class="glass sticky top-0 z-50">
            <div class="container mx-auto px-6 h-16 flex justify-between items-center">
                <span class="text-xl font-extrabold text-slate-900">LogicLife<span class="text-indigo-600">.</span></span>
                <div class="flex gap-6">
                    <a href="#products" class="text-sm font-bold text-slate-600 hover:text-indigo-600">Produk</a>
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
                        
                        <div class="text-slate-500 text-sm mb-6 prose">
                            {{ item.description | safe }}
                        </div>
                        
                        <div class="mt-auto pt-6 border-t border-slate-100">
                            <div class="flex flex-col mb-4">
                                <span class="text-xs line-through text-slate-400">Rp {{ item.original_price }}</span>
                                <div class="flex items-baseline gap-1">
                                    <span class="text-3xl font-extrabold text-slate-800">Rp {{ "{:,.0f}".format(item.price).replace(',', '.') }}</span>
                                    <span class="text-sm font-bold text-slate-500">{{ item.unit or '' }}</span>
                                </div>
                            </div>

                            <form action="/checkout" method="POST">
                                <input type="hidden" name="product_id" value="{{ item.id }}">
                                
                                <div class="mb-3">
                                    <label class="text-[10px] font-bold text-slate-400 uppercase block mb-1">Email Akun Anda (Untuk Aktivasi)</label>
                                    <input type="email" name="customer_email" placeholder="contoh@gmail.com" class="w-full border border-slate-300 bg-slate-50 px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-indigo-500 transition" required>
                                </div>

                                <div class="grid grid-cols-2 gap-2">
                                    {% if item.download_url %}
                                    <a href="{{ item.download_url }}" target="_blank" class="flex items-center justify-center bg-white border border-slate-300 text-slate-700 font-bold py-3 rounded-xl hover:bg-slate-50 hover:border-slate-400 transition shadow-sm gap-1 group">
                                        <svg class="w-5 h-5 text-slate-500 group-hover:text-indigo-600 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                                        <span class="text-sm">UNDUH</span>
                                    </a>
                                    {% else %}
                                    <div class="flex items-center justify-center bg-slate-100 text-slate-400 font-bold py-3 rounded-xl text-sm cursor-not-allowed border border-slate-200">
                                        Coming Soon
                                    </div>
                                    {% endif %}

                                    <button type="submit" class="bg-slate-900 text-white font-bold py-3 rounded-xl hover:bg-indigo-600 transition shadow-lg flex justify-center items-center gap-1 group">
                                        <svg class="w-5 h-5 text-yellow-400 group-hover:animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                                        <span class="text-sm">BELI PRO</span>
                                    </button>
                                </div>

                            </form>
                        </div>
                    </div>
                </div>
                {% else %}
                <div class="col-span-3 text-center py-20 text-slate-400">Belum ada produk. Silakan tambah di Admin.</div>
                {% endfor %}
            </div>
        </section>
        
        <footer class="bg-slate-900 text-slate-300 py-16 text-center relative overflow-hidden z-20">
            <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"></div>
            <div class="container mx-auto px-6 relative z-30">
                <div class="mb-8">
                    <p class="mb-2 font-bold text-white text-2xl tracking-tight">{{ contact.company }}</p>
                    <p class="text-slate-400 max-w-md mx-auto">{{ contact.address }}</p>
                </div>
                <div class="flex flex-wrap justify-center gap-4 mb-10">
                    <a href="https://wa.me/{{ contact.whatsapp }}" target="_blank" class="bg-white/5 hover:bg-white/10 border border-white/10 px-6 py-3 rounded-full flex items-center gap-2 transition text-sm font-bold text-white cursor-pointer">
                        WhatsApp Support
                    </a>
                    <a href="mailto:{{ contact.email }}" target="_blank" class="bg-white/5 hover:bg-white/10 border border-white/10 px-6 py-3 rounded-full flex items-center gap-2 transition text-sm font-bold text-white cursor-pointer">
                        {{ contact.email }}
                    </a>
                </div>
                <p class="text-xs text-slate-500">&copy; 2026 LogicLife Ecosystem.</p>
            </div>
        </footer>
    </body>
    </html>
    ''', products=products_data, contact=contact_data)

# ==============================================================================
# 💰 2. API PRICING
# ==============================================================================
@app.route('/api/get_pricing')
def get_pricing():
    app_id = request.args.get('app_id')
    price = 150000 
    
    if db:
        doc = db.collection('settings').document('pricing').get()
        if doc.exists:
            data = doc.to_dict()
            if app_id == 'moodly':
                price = data.get('moodly_price', 50000)
            else:
                price = data.get('nexapos_price', 150000)
    
    return jsonify({
        "app_id": app_id,
        "price": price,
        "formatted": "{:,.0f}".format(price).replace(',', '.')
    })

# ==============================================================================
# 🛒 3. PROSES BAYAR APLIKASI (DIRECT APP)
# ==============================================================================
@app.route('/buy_pro')
def buy_pro():
    uid = request.args.get('uid')
    email = request.args.get('email')
    app_id = request.args.get('app_id') 
    
    if not uid: return "Error: User ID tidak ditemukan."

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

    order_id = f"PRO-{app_id}-{uid}-{random.randint(100,999)}"
    signature_str = MERCHANT_CODE + order_id + str(product_price) + API_KEY
    signature = hashlib.md5(signature_str.encode('utf-8')).hexdigest()

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

    if resultCode == '00': 
        parts = merchantOrderId.split('-')
        if len(parts) >= 3:
            app_id = parts[1] 
            uid = parts[2]
            
            if db:
                field_to_update = 'is_pro'
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
# 🛒 4. CHECKOUT WEB (DENGAN EMAIL MATCHING)
# ==============================================================================
@app.route('/checkout', methods=['POST'])
def checkout():
    product_id = request.form.get('product_id')
    customer_email = request.form.get('customer_email') # 👇 Tangkap Email
    
    if not customer_email: return "Error: Email wajib diisi!"

    product = None
    if db:
        doc = db.collection('products').document(product_id).get()
        if doc.exists: product = doc.to_dict()
    
    if not product: return "Error: Produk tidak ditemukan."
    
    amount = int(product['price'])
    product_name = product['name']
    
    # Order ID Unik
    order_id = product['prefix'] + str(random.randint(10000, 99999))
    
    # 🔥 SIMPAN TRANSAKSI SEMENTARA (Buat cek email nanti)
    if db:
        db.collection('pending_transactions').document(order_id).set({
            'email': customer_email,
            'product_id': product_id,
            'product_name': product_name,
            'created_at': firestore.SERVER_TIMESTAMP,
            'status': 'pending'
        })

    signature_str = MERCHANT_CODE + order_id + str(amount) + API_KEY
    signature = hashlib.md5(signature_str.encode('utf-8')).hexdigest()
    
    payload = {
        "merchantCode": MERCHANT_CODE,
        "paymentAmount": amount,
        "merchantOrderId": order_id,
        "productDetails": product_name,
        "email": customer_email, 
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

# CALLBACK WEB
@app.route('/callback', methods=['POST'])
def callback():
    data = request.form
    merchantOrderId = data.get('merchantOrderId')
    resultCode = data.get('resultCode')

    if resultCode == '00': 
        if db:
            txn_ref = db.collection('pending_transactions').document(merchantOrderId)
            txn_doc = txn_ref.get()
            
            if txn_doc.exists:
                txn_data = txn_doc.to_dict()
                email = txn_data.get('email')
                product_name = txn_data.get('product_name', '').lower()
                
                users_ref = db.collection('users')
                query = users_ref.where('email', '==', email).limit(1).stream()
                
                user_found = False
                for user_doc in query:
                    user_found = True
                    uid = user_doc.id
                    
                    update_data = {}
                    if 'moodly' in product_name:
                        update_data = {'is_pro_moodly': True}
                    elif 'nexapos' in product_name:
                        update_data = {'is_pro': True}
                    
                    if update_data:
                        db.collection('users').document(uid).set(update_data, merge=True)
                
                if not user_found:
                    db.collection('prepaid_upgrades').document(email).set({
                        'product_name': product_name,
                        'paid_at': firestore.SERVER_TIMESTAMP
                    })

                txn_ref.update({'status': 'success'})

    return "OK"

@app.route('/finish')
def finish(): return "<h1>Transaksi Selesai! Terima kasih.</h1>"

# ==============================================================================
# 🔐 5. ADMIN PANEL (LENGKAP + EDITOR + EDIT + UNIT)
# ==============================================================================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('pin') == ADMIN_PIN:
            session['is_admin'] = True
            return redirect('/admin')
        else: return "PIN SALAH!"

    if not session.get('is_admin'):
        return render_template_string('<form method="POST" style="text-align:center;padding:50px;font-family:sans-serif;"><h2>Admin Login</h2><input type="password" name="pin" placeholder="PIN Rahasia" style="padding:10px;"><br><br><button style="padding:10px 20px;">Masuk</button></form>')

    products_data = []
    contact_data = {"company": "", "address": "", "whatsapp": "", "email": ""}
    pricing_data = {"nexapos_price": 150000, "moodly_price": 50000} 

    if db:
        docs = db.collection('products').stream()
        for doc in docs:
            prod = doc.to_dict()
            prod['id'] = doc.id
            products_data.append(prod)
        
        settings_doc = db.collection('settings').document('contact').get()
        if settings_doc.exists: contact_data = settings_doc.to_dict()

        price_doc = db.collection('settings').document('pricing').get()
        if price_doc.exists: pricing_data = price_doc.to_dict()

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <title>Admin LogicLife</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.ckeditor.com/4.16.2/standard/ckeditor.js"></script>
    </head>
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
                        <input type="text" name="name" placeholder="Nama Produk" class="w-full border bg-slate-50 p-2 rounded" required>
                        <input type="text" name="tagline" placeholder="Tagline Pendek" class="w-full border bg-slate-50 p-2 rounded" required>
                        
                        <div class="grid grid-cols-3 gap-2">
                            <input type="number" name="price" placeholder="Harga Angka" class="col-span-1 w-full border bg-slate-50 p-2 rounded" required>
                            <input type="text" name="unit" placeholder="/tahun (Opsional)" class="col-span-1 w-full border bg-slate-50 p-2 rounded">
                            <input type="text" name="original_price" placeholder="Harga Coret" class="col-span-1 w-full border bg-slate-50 p-2 rounded" required>
                        </div>

                        <input type="text" name="prefix" placeholder="Prefix Order (Contoh: BOOK-)" class="w-full border bg-slate-50 p-2 rounded" required>
                        <input type="text" name="image_url" placeholder="Link Gambar (https://...)" class="w-full border bg-slate-50 p-2 rounded" required>
                        <input type="text" name="download_url" placeholder="Link Download File" class="w-full border bg-slate-50 p-2 rounded">
                        
                        <label class="text-xs font-bold uppercase mt-2">Deskripsi Produk</label>
                        <textarea name="description" placeholder="Deskripsi..." class="w-full border bg-slate-50 p-2 rounded" rows="3" required></textarea>
                        
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
                            <div class="flex items-center gap-1">
                                <p class="text-xs font-bold text-emerald-600">Rp {{ item.price }}</p>
                                <p class="text-xs text-slate-400">{{ item.unit or '' }}</p>
                            </div>
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

        <script>
            CKEDITOR.replace('description');
        </script>
    </body>
    </html>
    ''', products=products_data, contact=contact_data, pricing=pricing_data)

# ==============================================================================
# ⚙️ 6. ROUTE CRUD ADMIN (FULL EDIT)
# ==============================================================================
@app.route('/admin/settings', methods=['POST'])
def update_settings():
    if not session.get('is_admin'): return redirect('/admin')
    
    contact_data = {
        "company": request.form.get('company'), 
        "address": request.form.get('address'), 
        "whatsapp": request.form.get('whatsapp'), 
        "email": request.form.get('email').strip()
    }
    if db: db.collection('settings').document('contact').set(contact_data)

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
    data = { 
        "name": request.form.get('name'), 
        "tagline": request.form.get('tagline'), 
        "price": int(request.form.get('price')), 
        "unit": request.form.get('unit'), 
        "original_price": request.form.get('original_price'), 
        "prefix": request.form.get('prefix'), 
        "description": request.form.get('description'), 
        "image_url": request.form.get('image_url'), 
        "download_url": request.form.get('download_url'), 
        "created_at": firestore.SERVER_TIMESTAMP 
    }
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
    
    return render_template_string('''
    <!DOCTYPE html><html lang="id">
    <head>
        <title>Edit Produk</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.ckeditor.com/4.16.2/standard/ckeditor.js"></script>
    </head>
    <body class="bg-slate-100 p-10 flex justify-center min-h-screen items-center">
        <div class="bg-white p-8 rounded-xl shadow w-full max-w-2xl">
            <h2 class="font-bold text-xl mb-4 text-slate-700">✏️ Edit Produk Lengkap</h2>
            <form action="/admin/update/{{ product.id }}" method="POST" class="grid gap-3">
                
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="text-xs font-bold uppercase text-slate-500">Nama Produk</label>
                        <input type="text" name="name" value="{{ product.name }}" class="border p-2 w-full rounded bg-slate-50">
                    </div>
                    <div>
                        <label class="text-xs font-bold uppercase text-slate-500">Tagline</label>
                        <input type="text" name="tagline" value="{{ product.tagline }}" class="border p-2 w-full rounded bg-slate-50">
                    </div>
                </div>

                <div class="grid grid-cols-3 gap-2">
                    <div>
                        <label class="text-xs font-bold uppercase text-slate-500">Harga (Angka)</label>
                        <input type="number" name="price" value="{{ product.price }}" class="border p-2 w-full rounded bg-slate-50">
                    </div>
                    <div>
                        <label class="text-xs font-bold uppercase text-slate-500">Unit (/bulan)</label>
                        <input type="text" name="unit" value="{{ product.unit or '' }}" class="border p-2 w-full rounded bg-slate-50">
                    </div>
                    <div>
                        <label class="text-xs font-bold uppercase text-slate-500">Harga Coret</label>
                        <input type="text" name="original_price" value="{{ product.original_price }}" class="border p-2 w-full rounded bg-slate-50">
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="text-xs font-bold uppercase text-slate-500">Prefix Order</label>
                        <input type="text" name="prefix" value="{{ product.prefix }}" class="border p-2 w-full rounded bg-slate-50">
                    </div>
                    <div>
                        <label class="text-xs font-bold uppercase text-slate-500">Link Gambar</label>
                        <input type="text" name="image_url" value="{{ product.image_url }}" class="border p-2 w-full rounded bg-slate-50">
                    </div>
                </div>

                <div>
                    <label class="text-xs font-bold uppercase text-slate-500">Link Download</label>
                    <input type="text" name="download_url" value="{{ product.download_url }}" class="border p-2 w-full rounded bg-slate-50">
                </div>

                <label class="text-xs font-bold uppercase text-slate-500 mt-2">Deskripsi Produk</label>
                <textarea name="description" class="border p-2 w-full rounded">{{ product.description }}</textarea>
                
                <div class="flex gap-2 mt-4">
                    <a href="/admin" class="bg-gray-200 text-gray-700 py-3 rounded-lg font-bold w-1/3 text-center">BATAL</a>
                    <button class="bg-indigo-600 text-white w-2/3 py-3 rounded-lg font-bold shadow hover:bg-indigo-700">UPDATE DATA</button>
                </div>
            </form>
        </div>
        <script>CKEDITOR.replace('description');</script>
    </body></html>
    ''', product=product)

@app.route('/admin/update/<id>', methods=['POST'])
def update_product_logic(id):
    if not session.get('is_admin'): return redirect('/admin')
    
    data = { 
        "name": request.form.get('name'), 
        "tagline": request.form.get('tagline'),
        "price": int(request.form.get('price')), 
        "unit": request.form.get('unit'),
        "original_price": request.form.get('original_price'),
        "prefix": request.form.get('prefix'),
        "image_url": request.form.get('image_url'),
        "download_url": request.form.get('download_url'),
        "description": request.form.get('description') 
    }
    
    if db: db.collection('products').document(id).update(data)
    return redirect('/admin')

@app.route('/logout')
def logout(): session.pop('is_admin', None); return redirect('/')