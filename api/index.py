from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import hashlib
import requests
import random
import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore

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
        
        # Cek Koneksi Database
        if db is None:
            return "<h1>❌ ERROR FATAL: Database Tidak Terhubung!</h1><p>Variabel 'db' is None. Cek kredensial Firebase.</p>"
        logs.append("✅ 2. Database Terhubung")
        
        # Cek Pecahan ID
        parts = order_id.split('-')
        logs.append(f"ℹ️ 3. Pecahan ID: {parts} (Jumlah: {len(parts)})")
        
        app_id = 'nexapos'
        uid = None
        
        if len(parts) >= 4:
            app_id = parts[1]
            uid = parts[2]
        elif len(parts) == 3:
            uid = parts[1]
        else:
            return "<br>".join(logs) + "<br><h1>❌ GAGAL: Format ID Salah (Kurang panjang)</h1>"
            
        logs.append(f"🎯 4. Target: App={app_id}, UID={uid}")
        
        # Cek Apakah User Ada di Firebase?
        user_ref = db.collection('users').document(uid)
        doc = user_ref.get()
        
        if not doc.exists:
             return "<br>".join(logs) + f"<br><h1>❌ GAGAL: User UID {uid} Tidak Ditemukan di Database!</h1>"
        logs.append("✅ 5. User Ditemukan di Database")
        
        # Eksekusi Update
        logs.append("⚙️ 6. Mencoba Update Status...")
        if app_id == 'moodly':
            user_ref.update({'is_pro_moodly': True, 'is_premium': True})
        else:
            user_ref.update({'is_pro': True, 'is_premium': True})
            
        logs.append("🎉 7. UPDATE BERHASIL!")
        
        return "<br>".join(logs) + "<br><h1>✅ SUKSES! Status User Sudah Diupdate.</h1>"

    except Exception as e:
        return "<br>".join(logs) + f"<br><h1>❌ EXCEPTION ERROR: {str(e)}</h1>"