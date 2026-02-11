from flask import Flask, render_template_string, request, redirect, session, url_for
import hashlib
import requests
import random
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from flask import jsonify

app = Flask(__name__)
app.secret_key = 'rahasia_negara_bos_nexa'

# ==============================================================================
# ⚙️ KONFIGURASI (JANGAN LUPA ISI INI LAGI BOS!)
# ==============================================================================
MERCHANT_CODE = "DS28030"      # 👈 ISI KODE MERCHANT BARU
API_KEY = "58191656b8692a368c766a9ca4124ee0"      # 👈 ISI API KEY BARU

# URL DUITKU (Mode QRIS / Inquiry V2)
SANDBOX_URL = "https://sandbox.duitku.com/webapi/api/merchant/v2/inquiry"
PAYMENT_METHOD = "SP" # QRIS ShopeePay Sandbox

ADMIN_PIN = "M3isy4851"

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
                        
                        <p class="text-slate-500 text-sm mb-6 whitespace-pre-line leading-relaxed">{{ item.description }}</p>
                        
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
                <p class="text-xs text-slate-500">&copy; 2026 LogicLife Ecosystem. v3.1 (Text Fix)</p>
            </div>
        </footer>
    </body>
    </html>
    ''', products=products_data, contact=contact_data)


# ==============================================================================
# 💰 API PUBLIC (Untuk Aplikasi Mengambil Harga)
# ==============================================================================
@app.route('/api/get_pricing')
def get_pricing():
    price = 150000 # Default kalau database kosong
    if db:
        doc = db.collection('settings').document('pricing').get()
        if doc.exists:
            price = doc.to_dict().get('pro_price', 150000)
    
    return jsonify({
        "price": price,
        "formatted": "{:,.0f}".format(price).replace(',', '.')
    })

# ==============================================================================
# 🛒 PROSES PEMBAYARAN (Update biar harga dinamis)
# ==============================================================================
@app.route('/buy_pro')
def buy_pro():
    uid = request.args.get('uid')
    email = request.args.get('email')
    
    if not uid: return "Error: User ID tidak ditemukan."

    # 👇 AMBIL HARGA DARI DATABASE (JANGAN HARDCODE LAGI)
    product_price = 150000 
    if db:
        doc = db.collection('settings').document('pricing').get()
        if doc.exists:
            product_price = int(doc.to_dict().get('pro_price', 150000))

    order_id = f"PRO-{uid}-{random.randint(100,999)}"
    
    signature_str = MERCHANT_CODE + order_id + str(product_price) + API_KEY
    signature = hashlib.md5(signature_str.encode('utf-8')).hexdigest()

    payload = {
        "merchantCode": MERCHANT_CODE,
        "paymentAmount": product_price,
        "merchantOrderId": order_id,
        "productDetails": "NexaPOS PRO Lifetime",
        "email": email,
        "paymentMethod": "SP",
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

# ... (Route callback_pro & success_pro biarkan tetap sama) ...

# ==============================================================================
# ⚙️ UPDATE ADMIN PANEL (Tambah Menu Setting Harga)
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

    # 👇 Update Harga PRO
    pro_price = request.form.get('pro_price')
    if pro_price and db:
        db.collection('settings').document('pricing').set({'pro_price': int(pro_price)})

    return redirect('/admin')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # ... (Kode login admin tetap sama) ...

    # Load Data buat ditampilkan
    products_data = []
    contact_data = {"company": "", "address": "", "whatsapp": "", "email": ""}
    pricing_data = {"pro_price": 150000} # Default

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

        # 👇 Load Harga PRO
        price_doc = db.collection('settings').document('pricing').get()
        if price_doc.exists: pricing_data = price_doc.to_dict()

    # 👇 UPDATE TEMPLATE HTML ADMIN (TAMBAH INPUT HARGA)
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="id">
    <head><title>Admin LogicLife</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 p-10 font-sans">
        <div class="max-w-6xl mx-auto">
             <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div class="bg-white p-8 rounded-xl shadow-md border-t-4 border-emerald-500 h-fit">
                    <h2 class="text-xl font-bold mb-6 flex items-center gap-2 text-emerald-900">⚙️ Pengaturan Global</h2>
                    <form action="/admin/settings" method="POST" class="grid gap-4">
                        
                        <div class="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                            <label class="block text-xs font-bold text-yellow-800 uppercase mb-1">Harga Paket PRO (Lifetime)</label>
                            <div class="flex items-center gap-2">
                                <span class="font-bold text-slate-500">Rp</span>
                                <input type="number" name="pro_price" value="{{ pricing.pro_price }}" class="w-full border bg-white p-2 rounded-lg font-bold text-slate-800" required>
                            </div>
                        </div>

                        <hr class="border-slate-200 my-2">

                        <label class="text-xs font-bold text-slate-500 uppercase">Nama Perusahaan</label>
                        <input type="text" name="company" value="{{ contact.company }}" class="w-full border bg-slate-50 p-3 rounded-lg" required>
                        
                        <label class="text-xs font-bold text-slate-500 uppercase">Alamat</label>
                        <textarea name="address" class="w-full border bg-slate-50 p-3 rounded-lg" rows="3" required>{{ contact.address }}</textarea>
                        
                        <label class="text-xs font-bold text-slate-500 uppercase">WhatsApp Admin</label>
                        <input type="number" name="whatsapp" value="{{ contact.whatsapp }}" class="w-full border bg-slate-50 p-3 rounded-lg" required>
                        
                        <label class="text-xs font-bold text-slate-500 uppercase">Email Support</label>
                        <input type="email" name="email" value="{{ contact.email }}" class="w-full border bg-slate-50 p-3 rounded-lg" required>
                        
                        <button class="bg-emerald-600 text-white w-full py-3 rounded-lg font-bold hover:bg-emerald-700 shadow-lg mt-2">💾 SIMPAN PENGATURAN</button>
                    </form>
                </div>
            </div>
            
            </div>
    </body>
    </html>
    ''', products=products_data, contact=contact_data, pricing=pricing_data)
