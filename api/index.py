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
    if db:
        txn_ref = db.collection('pending_transactions').document(order_id)
        txn_doc = txn_ref.get()
        if txn_doc.exists:
            txn_data = txn_doc.to_dict()
            if txn_data.get('status') == 'success': return
            
            email = txn_data.get('email')
            product_name = txn_data.get('product_name', '').lower()
            
            users = db.collection('users').where('email', '==', email).limit(1).stream()
            user_found = False
            for u in users:
                user_found = True
                update = {'is_pro_moodly': True} if 'moodly' in product_name else ({'is_pro': True} if 'nexapos' in product_name else {})
                if update: db.collection('users').document(u.id).set(update, merge=True)
            
            if not user_found:
                db.collection('prepaid_upgrades').document(email).set({'product_name': product_name, 'paid_at': firestore.SERVER_TIMESTAMP})
            
            txn_ref.update({'status': 'success'})

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
    uid, email, app_id = request.args.get('uid'), request.args.get('email'), request.args.get('app_id')
    if not uid: return "Error: User ID tidak ditemukan."
    product_price, product_name = 150000, "NexaPOS PRO Lifetime"
    if db:
        doc = db.collection('settings').document('pricing').get()
        if doc.exists:
            data = doc.to_dict()
            if app_id == 'moodly': product_price, product_name = int(data.get('moodly_price', 50000)), "Moodly Premium"
            else: product_price = int(data.get('nexapos_price', 150000))

    order_id = f"PRO-{app_id}-{uid}-{random.randint(100,999)}"
    signature = hashlib.md5((DUITKU_MERCHANT_CODE + order_id + str(product_price) + DUITKU_API_KEY).encode('utf-8')).hexdigest()
    
    payload = {
        "merchantCode": DUITKU_MERCHANT_CODE, "paymentAmount": product_price, "merchantOrderId": order_id,
        "productDetails": product_name, "email": email, "paymentMethod": "SP",
        "callbackUrl": "https://logiclife.site/callback", "returnUrl": "https://logiclife.site/success_pro",
        "signature": signature, "expiryPeriod": 60
    }
    try:
        r = requests.post(DUITKU_URL, json=payload, headers={'Content-Type': 'application/json'})
        data = r.json()
        if 'paymentUrl' in data: return redirect(data['paymentUrl'])
        return f"Error: {data}"
    except Exception as e: return str(e)

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