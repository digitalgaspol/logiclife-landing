from flask import Flask, render_template_string, request, redirect, session, url_for
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
# ⚙️ KONFIGURASI (BAGIAN INI YANG DIPERBAIKI)
# ==============================================================================
MERCHANT_CODE = "DS28030"    # 👈 Ganti Kode Merchant
API_KEY = "58191656b8692a368c766a9ca4124ee0"    # 👈 Ganti API Key Sandbox

# 👇👇👇 INI URL YANG BARU (CREATE INVOICE) 👇👇👇
SANDBOX_URL = "https://sandbox.duitku.com/webapi/api/merchant/createInvoice"
# 👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆

ADMIN_PIN = "M3isy4851"            # 👈 PIN Admin

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
# 🌐 HALAMAN PUBLIK
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
            @keyframes blob {
                0% { transform: translate(0px, 0px) scale(1); }
                33% { transform: translate(30px, -50px) scale(1.1); }
                66% { transform: translate(-20px, 20px) scale(0.9); }
                100% { transform: translate(0px, 0px) scale(1); }
            }
            .animate-blob { animation: blob 7s infinite; }
            .animation-delay-2000 { animation-delay: 2s; }
            .animation-delay-4000 { animation-delay: 4s; }
            .glass { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.5); }
        </style>
    </head>
    <body class="bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 text-slate-800 min-h-screen relative">

        <div class="fixed top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
            <div class="absolute top-0 left-1/4 w-96 h-96 bg-purple-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
            <div class="absolute top-0 right-1/4 w-96 h-96 bg-yellow-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
            <div class="absolute -bottom-8 left-1/3 w-96 h-96 bg-pink-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>
        </div>

        <nav class="glass sticky top-0 z-50">
            <div class="container mx-auto px-6 h-16 flex justify-between items-center">
                <div class="flex items-center gap-2 group cursor-pointer">
                    <div class="w-10 h-10 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl flex items-center justify-center text-white shadow-lg group-hover:scale-105 transition duration-300">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                        </svg>
                    </div>
                    <div class="flex flex-col">
                        <span class="text-xl font-extrabold text-slate-900 tracking-tight leading-none">LogicLife<span class="text-indigo-600">.</span></span>
                        <span class="text-[0.6rem] font-bold text-slate-500 uppercase tracking-widest leading-none">Digital Ecosystem</span>
                    </div>
                </div>

                <div class="flex gap-6">
                    <a href="#products" class="text-sm font-bold text-slate-600 hover:text-indigo-600 transition">Produk</a>
                    <a href="#kontak" class="text-sm font-medium text-slate-500 hover:text-slate-900 transition">Kontak</a>
                </div>
            </div>
        </nav>

        <header class="pt-24 pb-20 px-6 text-center relative z-10">
            <div class="inline-block mb-4 px-4 py-1 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold tracking-widest uppercase border border-indigo-200">
                Future Technology
            </div>
            <h1 class="text-5xl md:text-7xl font-extrabold text-slate-900 mb-6 tracking-tight leading-tight">
                Solusi Digital <br>
                <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600">Tanpa Batas</span>
            </h1>
            <p class="text-lg md:text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed mb-8">
                Tingkatkan produktivitas bisnis dan kebahagiaan personal Anda dengan ekosistem aplikasi LogicLife.
            </p>
            <a href="#products" class="bg-slate-900 text-white px-8 py-3 rounded-full font-bold shadow-xl hover:shadow-2xl hover:bg-slate-800 transition transform hover:-translate-y-1 inline-block">
                Lihat Produk
            </a>
        </header>

        <section id="products" class="container mx-auto px-6 py-10 mb-20 relative z-10">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
                {% for item in products %}
                <div class="glass bg-white/80 rounded-3xl shadow-xl overflow-hidden flex flex-col hover:-translate-y-2 transition duration-300 group">
                    <div class="h-64 w-full bg-white relative overflow-hidden p-4 flex items-center justify-center">
                        <img src="{{ item.image_url }}" alt="{{ item.name }}" class="w-full h-full object-contain transition duration-500 group-hover:scale-105" onerror="this.src='https://placehold.co/600x400?text=No+Image'">
                        <div class="absolute top-4 right-4 bg-indigo-50/90 backdrop-blur px-3 py-1 rounded-full text-xs font-bold shadow-sm text-indigo-900 border border-indigo-100">
                            {{ item.prefix }} Premium
                        </div>
                    </div>
                    <div class="p-8 flex-grow flex flex-col bg-white/50">
                        <h2 class="text-2xl font-extrabold mb-1 text-slate-900">{{ item.name }}</h2>
                        <p class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600 text-sm font-bold mb-4">{{ item.tagline }}</p>
                        <p class="text-slate-500 text-sm mb-6">{{ item.description }}</p>
                        <div class="mt-auto pt-6 border-t border-slate-100">
                            <div class="flex justify-between items-center mb-4">
                                <span class="text-3xl font-extrabold text-slate-900">Rp {{ "{:,.0f}".format(item.price).replace(',', '.') }}</span>
                                <span class="text-xs line-through text-slate-400 bg-slate-100 px-2 py-1 rounded">Rp {{ item.original_price }}</span>
                            </div>
                            <div class="grid grid-cols-2 gap-2">
                                {% if item.download_url %}
                                <a href="{{ item.download_url }}" target="_blank" class="flex items-center justify-center bg-white border border-slate-300 text-slate-700 font-bold py-3 rounded-xl hover:bg-slate-50 transition shadow-sm gap-1">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                                    <span class="text-sm">UNDUH</span>
                                </a>
                                {% else %}
                                <button disabled class="bg-slate-100 text-slate-400 font-bold py-3 rounded-xl text-sm cursor-not-allowed">BELUM RILIS</button>
                                {% endif %}
                                <form action="/checkout" method="POST" class="flex-grow">
                                    <input type="hidden" name="product_id" value="{{ item.id }}">
                                    <button type="submit" class="w-full bg-gradient-to-r from-slate-900 to-slate-800 text-white font-bold py-3 rounded-xl hover:from-indigo-600 hover:to-purple-600 transition-all flex justify-center items-center gap-1 shadow-lg">
                                        <span class="text-sm">BELI LISENSI</span>
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
                {% else %}
                <div class="col-span-3 text-center py-20 text-slate-400">Belum ada produk.</div>
                {% endfor %}
            </div>
        </section>

        <footer id="kontak" class="bg-slate-900 text-slate-300 py-16 text-center relative overflow-hidden z-20">
            <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"></div>
            <div class="container mx-auto px-6 relative z-30">
                <div class="mb-8">
                    <div class="w-16 h-16 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 text-white shadow-xl shadow-indigo-900/50">
                         <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                        </svg>
                    </div>
                    <p class="mb-2 font-bold text-white text-2xl tracking-tight">{{ contact.company }}</p>
                    <p class="text-slate-400 max-w-md mx-auto">{{ contact.address }}</p>
                </div>
                <div class="flex flex-wrap justify-center gap-4 mb-10">
                    <a href="https://wa.me/{{ contact.whatsapp }}" target="_blank" class="bg-white/5 hover:bg-white/10 border border-white/10 px-6 py-3 rounded-full flex items-center gap-2 transition text-sm font-bold text-white relative z-40 cursor-pointer">WhatsApp Support</a>
                    <a href="mailto:{{ contact.email }}" target="_blank" class="bg-white/5 hover:bg-white/10 border border-white/10 px-6 py-3 rounded-full flex items-center gap-2 transition text-sm font-bold text-white relative z-40 cursor-pointer">{{ contact.email }}</a>
                </div>
                <p class="text-xs text-slate-500">&copy; 2026 LogicLife Ecosystem.</p>
            </div>
        </footer>
    </body>
    </html>
    ''', products=products_data, contact=contact_data)

# ==============================================================================
# 🔐 ADMIN PANEL
# ==============================================================================

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        pin = request.form.get('pin')
        if pin == ADMIN_PIN:
            session['is_admin'] = True
            return redirect('/admin')
        else: return "PIN SALAH!"

    if not session.get('is_admin'):
        return render_template_string('<form method="POST" style="text-align:center;padding:50px;"><input type="password" name="pin" placeholder="PIN Rahasia"><button>Masuk</button></form>')

    products_data = []
    contact_data = {"company": "", "address": "", "whatsapp": "", "email": ""}
    
    if db:
        docs = db.collection('products').stream()
        for doc in docs:
            prod = doc.to_dict()
            prod['id'] = doc.id
            products_data.append(prod)
        settings_doc = db.collection('settings').document('contact').get()
        if settings_doc.exists: contact_data = settings_doc.to_dict()

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="id">
    <head><title>Admin LogicLife</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 p-10 font-sans">
        <div class="max-w-6xl mx-auto">
            <div class="flex justify-between items-center mb-8 bg-white p-4 rounded-xl shadow-sm">
                <div class="flex items-center gap-2">
                    <span class="text-2xl">⚙️</span>
                    <h1 class="text-2xl font-bold text-slate-800">Admin Dashboard</h1>
                </div>
                <div class="gap-2 flex">
                    <a href="/" class="bg-slate-800 text-white px-5 py-2 rounded-lg hover:bg-slate-900 font-bold text-sm">🏠 Lihat Web</a>
                    <a href="/logout" class="bg-red-500 text-white px-5 py-2 rounded-lg hover:bg-red-600 font-bold text-sm">🚪 Keluar</a>
                </div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div class="bg-white p-8 rounded-xl shadow-md border-t-4 border-indigo-600">
                    <h2 class="text-xl font-bold mb-6 flex items-center gap-2 text-indigo-900">📦 Tambah Produk Baru</h2>
                    <form action="/admin/add" method="POST" class="grid gap-4">
                        <input type="text" name="image_url" placeholder="Link Gambar (https://...)" class="w-full border bg-slate-50 p-3 rounded-lg" required>
                        <input type="text" name="name" placeholder="Nama Produk" class="w-full border bg-slate-50 p-3 rounded-lg" required>
                        <input type="text" name="tagline" placeholder="Tagline" class="w-full border bg-slate-50 p-3 rounded-lg" required>
                        <div class="grid grid-cols-2 gap-4">
                            <input type="number" name="price" placeholder="Harga" class="w-full border bg-slate-50 p-3 rounded-lg" required>
                            <input type="text" name="original_price" placeholder="Harga Coret" class="w-full border bg-slate-50 p-3 rounded-lg" required>
                        </div>
                        <input type="text" name="prefix" placeholder="Prefix (MOOD-)" class="w-full border bg-slate-50 p-3 rounded-lg" required>
                        <input type="text" name="download_url" placeholder="Link PlayStore / APK (Boleh Kosong)" class="w-full border bg-slate-50 p-3 rounded-lg border-blue-300">
                        <textarea name="description" placeholder="Deskripsi" class="w-full border bg-slate-50 p-3 rounded-lg" rows="3" required></textarea>
                        <button class="bg-indigo-600 text-white w-full py-3 rounded-lg font-bold hover:bg-indigo-700 shadow-lg mt-2">+ SIMPAN PRODUK</button>
                    </form>
                </div>
                <div class="bg-white p-8 rounded-xl shadow-md border-t-4 border-emerald-500 h-fit">
                    <h2 class="text-xl font-bold mb-6 flex items-center gap-2 text-emerald-900">📞 Edit Kontak</h2>
                    <form action="/admin/settings" method="POST" class="grid gap-4">
                        <input type="text" name="company" value="{{ contact.company }}" class="w-full border bg-slate-50 p-3 rounded-lg" required>
                        <textarea name="address" class="w-full border bg-slate-50 p-3 rounded-lg" rows="3" required>{{ contact.address }}</textarea>
                        <input type="number" name="whatsapp" value="{{ contact.whatsapp }}" class="w-full border bg-slate-50 p-3 rounded-lg" required>
                        <input type="email" name="email" value="{{ contact.email }}" class="w-full border bg-slate-50 p-3 rounded-lg" required>
                        <button class="bg-emerald-600 text-white w-full py-3 rounded-lg font-bold hover:bg-emerald-700 shadow-lg mt-2">💾 UPDATE KONTAK</button>
                    </form>
                </div>
            </div>
            <div class="mt-12">
                <h2 class="text-xl font-bold mb-4 text-slate-700">📋 Daftar Produk Aktif</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {% for item in products %}
                    <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex flex-col gap-3">
                        <div class="flex gap-4 items-center">
                            <img src="{{ item.image_url }}" class="w-16 h-16 object-contain rounded-lg bg-gray-100 p-1">
                            <div class="flex-grow">
                                <h3 class="font-bold text-slate-800">{{ item.name }}</h3>
                                <p class="text-slate-500 text-xs font-bold">Rp {{ item.price }}</p>
                            </div>
                        </div>
                        <div class="flex gap-2 mt-2">
                            <a href="/admin/edit/{{ item.id }}" class="bg-yellow-100 text-yellow-700 py-2 px-4 rounded-lg hover:bg-yellow-200 font-bold text-xs flex-grow text-center">✏️ EDIT</a>
                            <a href="/admin/delete/{{ item.id }}" onclick="return confirm('Yakin hapus?')" class="bg-red-50 text-red-600 py-2 px-4 rounded-lg hover:bg-red-100 font-bold text-xs flex-grow text-center">🗑️ HAPUS</a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </body>
    </html>
    ''', products=products_data, contact=contact_data)

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
    <!DOCTYPE html>
    <html lang="id">
    <head><title>Edit Produk</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 p-10 font-sans flex justify-center items-center min-h-screen">
        <div class="bg-white p-8 rounded-xl shadow-lg border-t-4 border-yellow-500 w-full max-w-lg">
            <h2 class="text-2xl font-bold mb-6 text-yellow-800">✏️ Edit Produk</h2>
            <form action="/admin/update/{{ product.id }}" method="POST" class="grid gap-4">
                <div><label class="text-xs font-bold text-slate-500 uppercase">Link Gambar</label><input type="text" name="image_url" value="{{ product.image_url }}" class="w-full border bg-slate-50 p-3 rounded-lg" required></div>
                <div><label class="text-xs font-bold text-slate-500 uppercase">Nama Produk</label><input type="text" name="name" value="{{ product.name }}" class="w-full border bg-slate-50 p-3 rounded-lg" required></div>
                <div><label class="text-xs font-bold text-slate-500 uppercase">Tagline</label><input type="text" name="tagline" value="{{ product.tagline }}" class="w-full border bg-slate-50 p-3 rounded-lg" required></div>
                <div class="grid grid-cols-2 gap-4">
                    <div><label class="text-xs font-bold text-slate-500 uppercase">Harga</label><input type="number" name="price" value="{{ product.price }}" class="w-full border bg-slate-50 p-3 rounded-lg" required></div>
                    <div><label class="text-xs font-bold text-slate-500 uppercase">Harga Coret</label><input type="text" name="original_price" value="{{ product.original_price }}" class="w-full border bg-slate-50 p-3 rounded-lg" required></div>
                </div>
                <div><label class="text-xs font-bold text-slate-500 uppercase">Prefix</label><input type="text" name="prefix" value="{{ product.prefix }}" class="w-full border bg-slate-50 p-3 rounded-lg" required></div>
                <div><label class="text-xs font-bold text-slate-500 uppercase">Link Download</label><input type="text" name="download_url" value="{{ product.download_url }}" class="w-full border bg-slate-50 p-3 rounded-lg border-blue-300"></div>
                <div><label class="text-xs font-bold text-slate-500 uppercase">Deskripsi</label><textarea name="description" class="w-full border bg-slate-50 p-3 rounded-lg" rows="3" required>{{ product.description }}</textarea></div>
                <div class="flex gap-2 mt-4"><a href="/admin" class="bg-gray-200 text-gray-700 py-3 rounded-lg font-bold w-1/3 text-center">BATAL</a><button class="bg-yellow-500 text-white w-2/3 py-3 rounded-lg font-bold hover:bg-yellow-600 shadow-lg">UPDATE DATA</button></div>
            </form>
        </div>
    </body>
    </html>
    ''', product=product)

@app.route('/admin/update/<id>', methods=['POST'])
def update_product_logic(id):
    if not session.get('is_admin'): return redirect('/admin')
    data = { "name": request.form.get('name'), "tagline": request.form.get('tagline'), "price": int(request.form.get('price')), "original_price": request.form.get('original_price'), "prefix": request.form.get('prefix'), "description": request.form.get('description'), "image_url": request.form.get('image_url'), "download_url": request.form.get('download_url') }
    if db: db.collection('products').document(id).update(data)
    return redirect('/admin')

@app.route('/logout')
def logout(): session.pop('is_admin', None); return redirect('/')

@app.route('/admin/settings', methods=['POST'])
def update_settings():
    if not session.get('is_admin'): return redirect('/admin')
    data = {"company": request.form.get('company'), "address": request.form.get('address'), "whatsapp": request.form.get('whatsapp'), "email": request.form.get('email').strip()}
    if db: db.collection('settings').document('contact').set(data)
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
    
    # PAYLOAD SAMA, TAPI SEKARANG DIKIRIM KE URL YANG BARU
    payload = {
        "merchantCode": MERCHANT_CODE, "paymentAmount": amount, "merchantOrderId": order_id,
        "productDetails": product_name, "email": "customer@example.com", "phoneNumber": "08123456789",
        "itemDetails": [{ "name": product_name, "price": amount, "quantity": 1 }],
        "customerDetail": { "firstName": "Customer", "lastName": "LogicLife", "email": "customer@example.com", "phoneNumber": "08123456789" },
        "callbackUrl": "https://logiclife.site/callback", "returnUrl": "https://logiclife.site/finish",
        "signature": signature, "expiryPeriod": 60
    }
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SANDBOX_URL, json=payload, headers=headers)
        data = response.json()
        if 'paymentUrl' in data: return redirect(data['paymentUrl'])
        return f"Error Duitku: {data}"
    except Exception as e: return str(e)