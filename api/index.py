from flask import Flask, render_template, request, redirect, session, url_for, jsonify
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
# 🌐 ROUTE UTAMA (MENGGUNAKAN TEMPLATE)
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
    
    # 👇 Render file templates/home.html
    return render_template('home.html', products=products_data, contact=contact_data)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('pin') == ADMIN_PIN:
            session['is_admin'] = True
            return redirect('/admin')
        else: return "PIN SALAH!"

    if not session.get('is_admin'):
        # 👇 Render file templates/login.html
        return render_template('login.html')

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

    # 👇 Render file templates/admin.html
    return render_template('admin.html', products=products_data, contact=contact_data, pricing=pricing_data)

@app.route('/admin/edit/<id>')
def edit_product_page(id):
    if not session.get('is_admin'): return redirect('/admin')
    product = {}
    if db:
        doc = db.collection('products').document(id).get()
        if doc.exists:
            product = doc.to_dict()
            product['id'] = doc.id
    
    # 👇 Render file templates/edit_product.html
    return render_template('edit_product.html', product=product)

# ==============================================================================
# ⚙️ API & LOGIC (TIDAK BERUBAH)
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
    uid, email, app_id = request.args.get('uid'), request.args.get('email'), request.args.get('app_id')
    if not uid: return "Error: User ID tidak ditemukan."
    product_price, product_name = 150000, "NexaPOS PRO Lifetime"
    
    if db:
        doc = db.collection('settings').document('pricing').get()
        if doc.exists:
            data = doc.to_dict()
            if app_id == 'moodly':
                product_price = int(data.get('moodly_price', 50000))
                product_name = "Moodly Premium"
            else:
                product_price = int(data.get('nexapos_price', 150000))

    order_id = f"PRO-{app_id}-{uid}-{random.randint(100,999)}"
    signature = hashlib.md5((MERCHANT_CODE + order_id + str(product_price) + API_KEY).encode('utf-8')).hexdigest()

    payload = {
        "merchantCode": MERCHANT_CODE, "paymentAmount": product_price, "merchantOrderId": order_id,
        "productDetails": product_name, "email": email, "paymentMethod": PAYMENT_METHOD,
        "callbackUrl": "https://logiclife.site/callback_pro", "returnUrl": "https://logiclife.site/success_pro",
        "signature": signature, "expiryPeriod": 60
    }
    try:
        r = requests.post(SANDBOX_URL, json=payload, headers={'Content-Type': 'application/json'})
        data = r.json()
        if 'paymentUrl' in data: return redirect(data['paymentUrl'])
        return f"Error Duitku: {data}"
    except Exception as e: return str(e)

@app.route('/callback_pro', methods=['POST'])
def callback_pro():
    data = request.form
    if data.get('resultCode') == '00':
        parts = data.get('merchantOrderId').split('-')
        if len(parts) >= 3:
            app_id, uid = parts[1], parts[2]
            if db:
                field = 'is_pro_moodly' if app_id == 'moodly' else 'is_pro'
                db.collection('users').document(uid).set({field: True, f'{field}_since': firestore.SERVER_TIMESTAMP}, merge=True)
    return "OK"

@app.route('/success_pro')
def success_pro(): return "<h1>Pembayaran Berhasil! Silakan kembali ke Aplikasi.</h1>"

@app.route('/checkout', methods=['POST'])
def checkout():
    product_id, customer_email = request.form.get('product_id'), request.form.get('customer_email')
    if not customer_email: return "Error: Email wajib diisi!"
    product = None
    if db:
        doc = db.collection('products').document(product_id).get()
        if doc.exists: product = doc.to_dict()
    if not product: return "Error: Produk tidak ditemukan."
    
    amount = int(product['price'])
    order_id = product['prefix'] + str(random.randint(10000, 99999))
    
    if db:
        db.collection('pending_transactions').document(order_id).set({
            'email': customer_email, 'product_id': product_id, 'product_name': product['name'],
            'created_at': firestore.SERVER_TIMESTAMP, 'status': 'pending'
        })

    signature = hashlib.md5((MERCHANT_CODE + order_id + str(amount) + API_KEY).encode('utf-8')).hexdigest()
    payload = {
        "merchantCode": MERCHANT_CODE, "paymentAmount": amount, "merchantOrderId": order_id,
        "productDetails": product['name'], "email": customer_email, "paymentMethod": PAYMENT_METHOD,
        "callbackUrl": "https://logiclife.site/callback", "returnUrl": "https://logiclife.site/finish",
        "signature": signature, "expiryPeriod": 60
    }
    try:
        r = requests.post(SANDBOX_URL, json=payload, headers={'Content-Type': 'application/json'})
        data = r.json()
        if 'paymentUrl' in data: return redirect(data['paymentUrl'])
        return f"Error Duitku: {data}"
    except Exception as e: return str(e)

@app.route('/callback', methods=['POST'])
def callback():
    data = request.form
    if data.get('resultCode') == '00':
        if db:
            txn_ref = db.collection('pending_transactions').document(data.get('merchantOrderId'))
            txn_doc = txn_ref.get()
            if txn_doc.exists:
                txn_data = txn_doc.to_dict()
                email, product_name = txn_data.get('email'), txn_data.get('product_name', '').lower()
                
                users = db.collection('users').where('email', '==', email).limit(1).stream()
                user_found = False
                for u in users:
                    user_found = True
                    update = {'is_pro_moodly': True} if 'moodly' in product_name else ({'is_pro': True} if 'nexapos' in product_name else {})
                    if update: db.collection('users').document(u.id).set(update, merge=True)
                
                if not user_found:
                    db.collection('prepaid_upgrades').document(email).set({'product_name': product_name, 'paid_at': firestore.SERVER_TIMESTAMP})
                txn_ref.update({'status': 'success'})
    return "OK"

@app.route('/finish')
def finish(): return "<h1>Transaksi Selesai! Terima kasih.</h1>"

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

@app.route('/logout')
def logout(): session.pop('is_admin', None); return redirect('/')