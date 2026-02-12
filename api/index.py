from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import random
import datetime

# ==============================================================================
# 1. INISIALISASI DATABASE & APP
# ==============================================================================

app = Flask(__name__)
CORS(app)

# 🔑 WAJIB ADA: Secret Key untuk fitur Flash Message (Notifikasi)
app.secret_key = os.environ.get('SECRET_KEY', 'rahasia_negara_logiclife_2026')

# --- DATABASE UTAMA (NEXAPOS) ---
db = None
try:
    cred = None
    if os.environ.get('FIREBASE_CREDENTIALS'):
        cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
        cred = credentials.Certificate(cred_dict)
    elif os.path.exists("api/serviceAccountKey.json"):
        cred = credentials.Certificate("api/serviceAccountKey.json")

    if cred:
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Koneksi NexaPOS: OK")
    else:
        print("⚠️ Warning: Kunci NexaPOS tidak ditemukan.")
except Exception as e:
    print(f"❌ Error Init NexaPOS: {e}")

# --- DATABASE KEDUA (MOODLY) ---
db_moodly = None
try:
    cred_moodly = None
    if os.environ.get('MOODLY_CREDENTIALS'):
        try:
            moodly_dict = json.loads(os.environ.get('MOODLY_CREDENTIALS'))
            cred_moodly = credentials.Certificate(moodly_dict)
        except json.JSONDecodeError:
            print("❌ Error JSON Moodly di Vercel rusak.")
    elif os.path.exists("api/moodly_key.json"):
        cred_moodly = credentials.Certificate("api/moodly_key.json")

    if cred_moodly:
        try:
            app_moodly = firebase_admin.get_app('moodly_app')
        except ValueError:
            app_moodly = firebase_admin.initialize_app(cred_moodly, name='moodly_app')
        
        db_moodly = firestore.client(app=app_moodly)
        print("✅ Koneksi Moodly: OK")
    else:
        print("⚠️ Warning: Kunci Moodly tidak ditemukan.")
except Exception as e:
    print(f"❌ Error Init Moodly: {e}")


# ==============================================================================
# 2. FUNGSI LOGIKA (FULFILL ORDER)
# ==============================================================================

def fulfill_order(order_id):
    """
    Fungsi Sakti: Mengubah status user jadi PREMIUM.
    """
    try:
        print(f"🔄 Processing Order: {order_id}")
        
        # Format Order ID: PRO-{APP}-{UID}-{RANDOM/MANUAL}
        if order_id.startswith('PRO-'):
            parts = order_id.split('-')
            
            if len(parts) >= 4:
                app_id = parts[1] # 'moodly' atau 'nexapos'
                uid = parts[2]
                
                # --- LOGIKA MOODLY ---
                if app_id == 'moodly':
                    if db_moodly:
                        user_ref = db_moodly.collection('users').document(uid)
                        user_ref.update({
                            'is_pro_moodly': True,
                            'is_premium': True,
                            'updated_at': firestore.SERVER_TIMESTAMP
                        })
                        print(f"✅ SUKSES MOODLY: User {uid} Updated!")
                        return True
                    else:
                        print("❌ GAGAL: Database Moodly belum terkoneksi.")
                        return False
                
                # --- LOGIKA NEXAPOS ---
                else: 
                    if db:
                        db.collection('users').document(uid).update({'is_pro': True, 'is_premium': True})
                        print(f"✅ SUKSES NEXAPOS: User {uid} Updated!")
                        return True
                    else:
                        print("❌ GAGAL: Database NexaPOS belum terkoneksi.")
                        return False

        print(f"⚠️ Order ID {order_id} format tidak dikenal.")
        return False

    except Exception as e:
        print(f"❌ ERROR FULFILL SYSTEM: {e}")
        return False

# ==============================================================================
# 3. ROUTE / HALAMAN WEBSITE
# ==============================================================================

@app.route('/')
def home():
    return render_template('index.html')

# --- ROUTE ADMIN DASHBOARD (TAMPILAN) ---
@app.route('/admin')
def admin_dashboard():
    # Di sini bisa ditambah logika cek login session kalau mau aman
    # Untuk sekarang kita render langsung biar Bos bisa masuk
    
    # Data Dummy untuk tampilan (Supaya gak error variablenya)
    pricing = {'nexapos_price': 150000, 'moodly_price': 50000}
    contact = {'company': 'LogicLife', 'email': 'admin@logiclife.site'}
    products = [] # List kosong dulu
    
    return render_template('admin.html', pricing=pricing, contact=contact, products=products)


# --- ROUTE ADMIN ACTION (AKTIVASI MANUAL) ---
@app.route('/admin/activate_user', methods=['POST'])
def admin_activate_user():
    uid = request.form.get('uid', '').strip()
    app_type = request.form.get('app_type')
    
    # Ambil PIN (Opsional, sudah saya matikan pengecekannya biar Bos lolos)
    pin = request.form.get('pin', '').strip()
    
    # 🔓 PIN CHECKER DIMATIKAN SEMENTARA 🔓
    # if pin != "123456":
    #    flash("❌ PIN SALAH!", "error")
    #    return redirect('/admin')
    
    if not uid:
        flash("❌ UID Kosong! Copy dari WA dulu bos.", "error")
        return redirect('/admin')

    # Buat Order ID Palsu untuk memancing fungsi fulfill_order
    fake_order_id = f"PRO-{app_type}-{uid}-MANUAL"
    
    # Eksekusi
    if fulfill_order(fake_order_id):
        nama_app = "MOODLY" if app_type == 'moodly' else "NEXAPOS"
        flash(f"✅ BERHASIL! User {uid} sudah PREMIUM di {nama_app}.", "success")
    else:
        flash("❌ GAGAL! Cek server logs (Vercel) untuk detail error.", "error")

    return redirect('/admin')


# --- WEBHOOK MIDTRANS ---
@app.route('/callback_midtrans', methods=['POST'])
def callback_midtrans():
    try:
        notification = request.get_json()
        order_id = notification.get('order_id')
        transaction_status = notification.get('transaction_status')
        
        if transaction_status in ['capture', 'settlement']:
            fulfill_order(order_id)
        
        return "OK", 200
    except Exception as e:
        return "Error", 500

# --- DEBUG MANUAL (LINK LAMA) ---
@app.route('/debug_order/<order_id>')
def debug_order(order_id):
    if fulfill_order(order_id):
        return f"<h1>BERHASIL ✅</h1> Order {order_id} diproses."
    return f"<h1>GAGAL ❌</h1> Cek logs."

if __name__ == '__main__':
    app.run(debug=True)