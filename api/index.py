from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from firebase_admin import credentials, firestore
from flask_cors import CORS
import hashlib
import requests
import random
import os
import json
import base64
import firebase_admin
import datetime


app = Flask(__name__)
app.secret_key = 'rahasia_negara_bos_nexa'

# ==============================================================================
# ⚙️ KONFIGURASI PAYMENT GATEWAY (MODE AMAN - PULL DARI ENVIRONMENT)
# ==============================================================================

# 1. DUITKU
DUITKU_MERCHANT_CODE = os.environ.get("DUITKU_MERCHANT_CODE", "DS28030")      
DUITKU_API_KEY = os.environ.get("DUITKU_API_KEY", "58191656b8692a368c766a9ca4124ee0")      
DUITKU_URL = "https://sandbox.duitku.com/webapi/api/merchant/v2/inquiry"

# 2. MIDTRANS (Gunakan Environment Variable)
MIDTRANS_SERVER_KEY = os.environ.get("MIDTRANS_SERVER_KEY", "SB-Mid-server-xxxxxxxxxxxx") 
MIDTRANS_URL = "https://app.sandbox.midtrans.com/snap/v1/transactions" 

# 3. ADMIN
ADMIN_PIN = "M3isy4851"

# ==============================================================================
# 🔥 INIT FIREBASE
# ==============================================================================
# --- 1. INISIALISASI DATABASE NEXAPOS (UTAMA) ---
# Baca dari Brangkas Vercel: FIREBASE_CREDENTIALS
db = None
try:
    # Cek apakah jalan di Local (pakai file) atau Vercel (pakai Env)
    if os.environ.get('FIREBASE_CREDENTIALS'):
        cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
        cred = credentials.Certificate(cred_dict)
    else:
        # Fallback buat di Laptop (kalau ada filenya)
        cred = credentials.Certificate("api/serviceAccountKey.json")

    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    print("✅ Koneksi NexaPOS: OK")
except Exception as e:
    print(f"❌ Koneksi NexaPOS Gagal: {e}")

# --- 2. INISIALISASI DATABASE MOODLY (KEDUA) ---
# Baca dari Brangkas Vercel: MOODLY_CREDENTIALS
db_moodly = None
try:
    if os.environ.get('MOODLY_CREDENTIALS'):
        # Baca dari Brangkas Vercel
        moodly_dict = json.loads(os.environ.get('MOODLY_CREDENTIALS'))
        cred_moodly = credentials.Certificate(moodly_dict)
        
        try:
            app_moodly = firebase_admin.get_app('moodly_app')
        except ValueError:
            app_moodly = firebase_admin.initialize_app(cred_moodly, name='moodly_app')
            
        db_moodly = firestore.client(app=app_moodly)
        print("✅ Koneksi Moodly: OK (Via Env)")
        
    elif os.path.exists("api/moodly_key.json"):
        # Fallback buat di Laptop (kalau Bos taruh file manual saat dev)
        cred_moodly = credentials.Certificate("api/moodly_key.json")
        try:
            app_moodly = firebase_admin.get_app('moodly_app')
        except ValueError:
            app_moodly = firebase_admin.initialize_app(cred_moodly, name='moodly_app')
            
        db_moodly = firestore.client(app=app_moodly)
        print("✅ Koneksi Moodly: OK (Via File)")
        
    else:
        print("⚠️ Skip Moodly: Tidak ada ENV MOODLY_CREDENTIALS atau file moodly_key.json")

except Exception as e:
    print(f"⚠️ Koneksi Moodly Gagal: {e}")

app = Flask(__name__)
# ... Lanjut ke bawah kode Bos yang lain ...
# ==============================================================================
# 🌐 ROUTE UTAMA
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
    
    return render_template('home.html', products=products_data, contact=contact_data)

# ==============================================================================
# 🛒 CHECKOUT ENGINE (MULTI-GATEWAY)
# ==============================================================================
@app.route('/checkout', methods=['POST'])
def checkout():
    product_id = request.form.get('product_id')
    customer_email = request.form.get('customer_email')
    gateway = request.form.get('gateway') 
    
    if not customer_email: return "Error: Email wajib diisi!"
    if not gateway: gateway = 'duitku'

    product = None
    if db:
        doc = db.collection('products').document(product_id).get()
        if doc.exists: product = doc.to_dict()
    
    if not product: return "Error: Produk tidak ditemukan."
    
    amount = int(product['price'])
    order_id = product['prefix'] + str(random.randint(10000, 99999))
    
    if db:
        db.collection('pending_transactions').document(order_id).set({
            'email': customer_email,
            'product_id': product_id,
            'product_name': product['name'],
            'gateway': gateway,
            'amount': amount,
            'created_at': firestore.SERVER_TIMESTAMP,
            'status': 'pending'
        })

    if gateway == 'midtrans':
        return process_midtrans(order_id, amount, product['name'], customer_email)
    else:
        return process_duitku(order_id, amount, product['name'], customer_email)

# --- DUITKU ---
def process_duitku(order_id, amount, product_name, email):
    signature_str = DUITKU_MERCHANT_CODE + order_id + str(amount) + DUITKU_API_KEY
    signature = hashlib.md5(signature_str.encode('utf-8')).hexdigest()
    
    payload = {
        "merchantCode": DUITKU_MERCHANT_CODE, "paymentAmount": amount, "merchantOrderId": order_id,
        "productDetails": product_name, "email": email, "paymentMethod": "SP",
        "callbackUrl": "https://logiclife.site/callback", "returnUrl": "https://logiclife.site/finish",
        "signature": signature, "expiryPeriod": 60
    }
    try:
        r = requests.post(DUITKU_URL, json=payload, headers={'Content-Type': 'application/json'})
        data = r.json()
        if 'paymentUrl' in data: return redirect(data['paymentUrl'])
        return f"Error Duitku: {data}"
    except Exception as e: return str(e)

# --- MIDTRANS ---
def process_midtrans(order_id, amount, product_name, email):
    auth_string = MIDTRANS_SERVER_KEY + ":"
    auth_b64 = base64.b64encode(auth_string.encode()).decode()
    
    payload = {
        "transaction_details": { "order_id": order_id, "gross_amount": amount },
        "customer_details": { "email": email },
        "item_details": [{ "id": "ITEM1", "price": amount, "quantity": 1, "name": product_name }],
        "callbacks": { "finish": "https://logiclife.site/finish" }
    }
    
    try:
        headers = { "Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Basic {auth_b64}" }
        r = requests.post(MIDTRANS_URL, json=payload, headers=headers)
        data = r.json()
        if 'redirect_url' in data: return redirect(data['redirect_url'])
        return f"Error Midtrans: {data}"
    except Exception as e: return str(e)

# ==============================================================================
# 📩 CALLBACKS & LOGIC
# ==============================================================================
@app.route('/callback', methods=['POST'])
def callback_duitku():
    data = request.form
    if data.get('resultCode') == '00': fulfill_order(data.get('merchantOrderId'))
    return "OK"

@app.route('/callback_midtrans', methods=['POST'])
def callback_midtrans():
    try:
        notif = request.json
        status = notif.get('transaction_status')
        fraud = notif.get('fraud_status')
        if status == 'capture':
            if fraud != 'challenge': fulfill_order(notif.get('order_id'))
        elif status == 'settlement':
            fulfill_order(notif.get('order_id'))
        return jsonify({"status": "OK"})
    except Exception as e: return jsonify({"status": "Error", "message": str(e)}), 500

def fulfill_order(order_id):
    """
    Fungsi sakti untuk mengubah status user jadi PREMIUM
    Menerima format order_id: PRO-{APP_ID}-{UID}-{RANDOM}
    """
    try:
        print(f"Processing Order: {order_id}")
        
        # 1. Cek apakah ini transaksi Upgrade PRO
        if order_id.startswith('PRO-'):
            parts = order_id.split('-')
            
            # Variabel penampung
            uid = None
            app_id = 'nexapos' # Default kalau format lama

            # 2. Deteksi Format Baru (4 Bagian): PRO-moodly-UID-123
            if len(parts) >= 4:
                app_id = parts[1] # 'moodly' atau 'nexapos'
                uid = parts[2]    # UID user
            
            # 3. Deteksi Format Lama (3 Bagian): PRO-UID-123 (Khusus NexaPOS lama)
            elif len(parts) == 3:
                uid = parts[1]

            # 4. Eksekusi Update ke Firebase
            if uid and db:
                user_ref = db.collection('users').document(uid)
                
                if app_id == 'moodly':
                    # Update khusus Moodly
                    user_ref.update({
                        'is_pro_moodly': True,
                        'is_premium': True, # Cadangan biar aman
                        'updated_at': firestore.SERVER_TIMESTAMP
                    })
                    print(f"✅ SUKSES: User {uid} jadi PREMIUM MOODLY")
                else:
                    # Update NexaPOS
                    user_ref.update({
                        'is_pro': True, # Field lama NexaPOS
                        'is_premium': True,
                        'updated_at': firestore.SERVER_TIMESTAMP
                    })
                    print(f"✅ SUKSES: User {uid} jadi PREMIUM NEXAPOS")
                return True
                
    except Exception as e:
        print(f"❌ GAGAL FULFILL: {e}")
        return False
    
    return False

@app.route('/finish')
def finish(): return "<h1>Transaksi Selesai! Terima kasih.</h1>"

# ==============================================================================
# ⚙️ API & ADMIN (SAMA)
# ==============================================================================
@app.route('/api/get_pricing')
def get_pricing():
    app_id = request.args.get('app_id')
    price = 150000 
    if db:
        doc = db.collection('settings').document('pricing').get()
        if doc.exists:
            data = doc.to_dict()
            if app_id == 'moodly': price = data.get('moodly_price', 50000)
            else: price = data.get('nexapos_price', 150000)
    return jsonify({"app_id": app_id, "price": price, "formatted": "{:,.0f}".format(price).replace(',', '.')})

@app.route('/buy_pro')
def buy_pro():
    # 1. Tangkap Data dari Aplikasi
    uid = request.args.get('uid')
    email = request.args.get('email')
    app_id = request.args.get('app_id')
    
    if not uid or not email: return "Error: Data User tidak lengkap."
    
    # 2. Tentukan Nama Produk buat Tampilan
    product_name = "NexaPOS PRO"
    if app_id == 'moodly': product_name = "Moodly Premium"

    # 3. Tampilkan Halaman Pilih Pembayaran (Bukan langsung redirect)
    return render_template('payment.html', uid=uid, email=email, app_id=app_id, product_name=product_name)

@app.route('/process_app_payment')
def process_app_payment():
    # 1. Tangkap Data dari Pilihan User
    gateway = request.args.get('gateway')
    uid = request.args.get('uid')
    email = request.args.get('email')
    app_id = request.args.get('app_id')

    # 2. Cek Harga & Nama Produk
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

    # 3. Buat Order ID Unik
    # Format: PRO-APPID-UID-RANDOM
    order_id = f"PRO-{app_id}-{uid}-{random.randint(100,999)}"

    # 4. Simpan Transaksi Pending (PENTING: Biar Callback Nemu)
    if db:
        db.collection('pending_transactions').document(order_id).set({
            'email': email,
            'product_id': app_id, # moodly atau nexapos
            'product_name': product_name,
            'gateway': gateway,
            'amount': product_price,
            'created_at': firestore.SERVER_TIMESTAMP,
            'status': 'pending',
            'origin': 'app', # Penanda transaksi dari aplikasi
            'user_uid': uid
        })

    # 5. Arahkan ke Gateway Pilihan
    if gateway == 'midtrans':
        return process_midtrans(order_id, product_price, product_name, email)
    else:
        return process_duitku(order_id, product_price, product_name, email)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('pin') == ADMIN_PIN: session['is_admin'] = True; return redirect('/admin')
        else: return "PIN SALAH!"
    if not session.get('is_admin'): return render_template('login.html')
    products_data, contact_data, pricing_data = [], {}, {"nexapos_price": 150000, "moodly_price": 50000}
    if db:
        for doc in db.collection('products').stream():
            prod = doc.to_dict(); prod['id'] = doc.id; products_data.append(prod)
        if db.collection('settings').document('contact').get().exists: contact_data = db.collection('settings').document('contact').get().to_dict()
        if db.collection('settings').document('pricing').get().exists: pricing_data = db.collection('settings').document('pricing').get().to_dict()
    return render_template('admin.html', products=products_data, contact=contact_data, pricing=pricing_data)

@app.route('/admin/settings', methods=['POST'])
def update_settings():
    if not session.get('is_admin'): return redirect('/admin')
    if db:
        db.collection('settings').document('contact').set({
            "company": request.form.get('company'), "address": request.form.get('address'),
            "whatsapp": request.form.get('whatsapp'), "email": request.form.get('email').strip()
        })
        db.collection('settings').document('pricing').set({
            'nexapos_price': int(request.form.get('nexapos_price')),
            'moodly_price': int(request.form.get('moodly_price'))
        }, merge=True)
    return redirect('/admin')

@app.route('/admin/add', methods=['POST'])
def add_product():
    if not session.get('is_admin'): return redirect('/admin')
    if db: db.collection('products').add({
        "name": request.form.get('name'), "tagline": request.form.get('tagline'),
        "price": int(request.form.get('price')), "unit": request.form.get('unit'),
        "original_price": request.form.get('original_price'), "prefix": request.form.get('prefix'),
        "description": request.form.get('description'), "image_url": request.form.get('image_url'),
        "download_url": request.form.get('download_url'), "created_at": firestore.SERVER_TIMESTAMP
    })
    return redirect('/admin')

@app.route('/admin/update/<id>', methods=['POST'])
def update_product_logic(id):
    if not session.get('is_admin'): return redirect('/admin')
    if db: db.collection('products').document(id).update({
        "name": request.form.get('name'), "tagline": request.form.get('tagline'),
        "price": int(request.form.get('price')), "unit": request.form.get('unit'),
        "original_price": request.form.get('original_price'), "prefix": request.form.get('prefix'),
        "image_url": request.form.get('image_url'), "download_url": request.form.get('download_url'),
        "description": request.form.get('description')
    })
    return redirect('/admin')

@app.route('/admin/delete/<id>')
def delete_product(id):
    if not session.get('is_admin'): return redirect('/admin')
    if db: db.collection('products').document(id).delete()
    return redirect('/admin')

@app.route('/admin/activate_user', methods=['POST'])
def admin_activate_user():
    uid = request.form.get('uid', '').strip()
    app_type = request.form.get('app_type')
    pin = request.form.get('pin')
    
    if pin != "851912": # Ganti PIN sesuai keinginan Bos
        flash("❌ PIN Salah!", "error")
        return redirect('/admin')
    
    if not uid:
        flash("❌ UID Kosong!", "error")
        return redirect('/admin')

    fake_order_id = f"PRO-{app_type}-{uid}-MANUAL"
    if fulfill_order(fake_order_id):
        flash(f"✅ SUKSES! User {uid} aktif di {app_type.upper()}.", "success")
    else:
        flash("❌ GAGAL! Cek server logs.", "error")

    return redirect('/admin')

@app.route('/admin/edit/<id>')
def edit_product_page(id):
    if not session.get('is_admin'): return redirect('/admin')
    product = {}
    if db:
        doc = db.collection('products').document(id).get(); 
        if doc.exists: product = doc.to_dict(); product['id'] = doc.id
    return render_template('edit_product.html', product=product)

@app.route('/logout')
def logout(): session.pop('is_admin', None); return redirect('/')

# ... (Baris terakhir kodingan lama Bos) ...

# 👇 TEMPEL INI DI PALING BAWAH FILE 👇
@app.route('/debug_order/<order_id>')
def debug_order(order_id):
    logs = []
    try:
        logs.append(f"🔍 1. Menerima Order ID: {order_id}")
        
        # Cek Koneksi
        if db: logs.append("✅ DB NexaPOS: Connected")
        else: logs.append("❌ DB NexaPOS: Disconnected")
        
        if db_moodly: logs.append("✅ DB Moodly: Connected")
        else: logs.append("❌ DB Moodly: Disconnected (Cek MOODLY_CREDENTIALS)")
        
        # Eksekusi Fulfill
        logs.append("⚙️ 2. Menjalankan fungsi fulfill_order()...")
        sukses = fulfill_order(order_id)
        
        if sukses:
            return "<br>".join(logs) + "<br><h1>✅ SUKSES BESAR! Cek App Sekarang.</h1>"
        else:
            return "<br>".join(logs) + "<br><h1>❌ GAGAL! Cek Logs Vercel untuk detail.</h1>"

    except Exception as e:
        return f"<h1>Error Fatal: {e}</h1>"

def fulfill_order(order_id):
    try:
        print(f"Processing Order: {order_id}")
        if order_id.startswith('PRO-'):
            parts = order_id.split('-')
            
            # Deteksi Format: PRO-moodly-UID-123
            if len(parts) >= 4:
                app_id = parts[1]
                uid = parts[2]
                
                if app_id == 'moodly':
                    if db_moodly:
                        db_moodly.collection('users').document(uid).update({
                            'is_pro_moodly': True, 
                            'is_premium': True,
                            'updated_at': firestore.SERVER_TIMESTAMP
                        })
                        return True
                    else:
                        print("❌ DB Moodly belum connect")
                        return False
                
                else:
                    # NexaPOS
                    if db:
                        db.collection('users').document(uid).update({'is_pro': True})
                        return True
            
            # Support Format Lama (NexaPOS)
            elif len(parts) == 3:
                uid = parts[1]
                if db:
                    db.collection('users').document(uid).update({'is_pro': True})
                    return True

    except Exception as e:
        print(f"Error: {e}")
        return False
    return False