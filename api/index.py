from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import random
import datetime
from firebase_admin import auth

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

# 👇 GANTI BAGIAN ROUTE HOME DENGAN INI 👇

@app.route('/')
def home():
    # 1. Siapkan Data Default (Supaya kalau DB error, web tetap jalan)
    products_data = []
    contact_data = {
        "company": "LogicLife Digital",
        "whatsapp": "628123456789", 
        "email": "admin@logiclife.site",
        "address": "Indonesia"
    }

    # 2. Ambil Data Real dari Database (NexaPOS)
    if db:
        try:
            # Ambil Produk
            docs = db.collection('products').stream()
            for doc in docs:
                prod = doc.to_dict()
                prod['id'] = doc.id
                products_data.append(prod)
            
            # Ambil Kontak (WA, Email, dll)
            settings_doc = db.collection('settings').document('contact').get()
            if settings_doc.exists:
                contact_data.update(settings_doc.to_dict())
                
        except Exception as e:
            print(f"⚠️ Error di Home: {e}")

    # 3. Render Template
    # ⚠️ PENTING: Pastikan nama file di folder templates adalah 'home.html'
    # Kalau nama filenya 'index.html', ganti jadi 'index.html' di bawah ini.
    return render_template('home.html', products=products_data, contact=contact_data)

# --- ROUTE ADMIN DASHBOARD (TAMPILAN) ---
# 👇 UPDATE BAGIAN INI BIAR PRODUKNYA MUNCUL LAGI 👇
# 👇 TAMBAHKAN KODE INI UNTUK LOGIN & LOGOUT 👇

# Konfigurasi PIN Admin (Bisa diganti)
ADMIN_PIN = "M3isy4851"

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    error = None
    if request.method == 'POST':
        pin = request.form.get('pin')
        if pin == ADMIN_PIN:
            session['is_admin'] = True # Simpan "Tiket Masuk"
            return redirect('/admin') # Arahkan ke Dashboard
        else:
            error = "❌ PIN Salah Bos!"
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear() # Robek tiket masuk
    return redirect('/login')

# 👇 UPDATE ROUTE ADMIN JADI TERKUNCI 👇

@app.route('/admin')
def admin_dashboard():
    # 🔒 CEK TIKET: Kalau belum login, tendang ke halaman login
    if not session.get('is_admin'):
        return redirect('/login')

    # ... (Logika ambil data database yg lama tetap sama di sini) ...
    # Copy logika ambil data products_data, pricing, dll dari kode sebelumnya ke sini
    
    products_data = []
    pricing_data = {"nexapos_price": 150000, "moodly_price": 50000}
    contact_data = {"company": "LogicLife", "email": "admin@logiclife.site"}

    if db:
        try:
            docs = db.collection('products').stream()
            for doc in docs:
                prod = doc.to_dict(); prod['id'] = doc.id; products_data.append(prod)
            
            p_doc = db.collection('settings').document('pricing').get()
            if p_doc.exists: pricing_data = p_doc.to_dict()

            c_doc = db.collection('settings').document('contact').get()
            if c_doc.exists: contact_data = c_doc.to_dict()
        except: pass

    return render_template('admin.html', products=products_data, pricing=pricing_data, contact=contact_data)


# --- ROUTE ADMIN ACTION (AKTIVASI MANUAL) ---
@app.route('/admin/activate_user', methods=['POST'])
def admin_activate_user():
    # 1. Ambil Data
    uid = request.form.get('uid', '').strip()
    app_type = request.form.get('app_type')
    pin = request.form.get('pin', '').strip() # Ambil PIN yang diketik
    
    # 2. 🔒 CEK PIN ADMIN (SUDAH AKTIF) 🔒
    # Ganti "123456" dengan PIN Rahasia Bos (Misal: "M3isy4851")
    if pin != "M3isy4851":
        flash("❌ PIN SALAH! Jangan coba-coba ya.", "error")
        return redirect('/admin')
    
    # 3. Validasi UID
    if not uid:
        flash("❌ UID Kosong! Copy dari WA dulu bos.", "error")
        return redirect('/admin')

    # 4. Buat Order ID Palsu & Eksekusi
    fake_order_id = f"PRO-{app_type}-{uid}-MANUAL"
    
    if fulfill_order(fake_order_id):
        nama_app = "MOODLY" if app_type == 'moodly' else "NEXAPOS"
        flash(f"✅ BERHASIL! User {uid} sudah PREMIUM di {nama_app}.", "success")
    else:
        flash("❌ GAGAL! Cek server logs.", "error")

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

# 👇 ROUTE HALAMAN EDIT (Pasang ini biar Error 404 hilang) 👇

@app.route('/admin/edit/<id>')
def edit_product_page(id):
    # Cek Login Admin
    # if not session.get('is_admin'): return redirect('/admin') # (Opsional: Nyalakan kalau mau aman)
    
    product = {}
    if db:
        try:
            doc = db.collection('products').document(id).get()
            if doc.exists: 
                product = doc.to_dict()
                product['id'] = doc.id # Masukkan ID biar form tau siapa yang diedit
            else:
                return "❌ Produk tidak ditemukan di Database."
        except Exception as e:
            return f"❌ Error Database: {e}"

    # Pastikan file 'edit_product.html' sudah ada di folder templates!
    return render_template('edit_product.html', product=product)


# 👇 ROUTE PROSES SIMPAN EDIT (Biar tombol Simpan berfungsi) 👇

@app.route('/admin/update/<id>', methods=['POST'])
def update_product_logic(id):
    # Cek Login Admin
    # if not session.get('is_admin'): return redirect('/admin') 
    
    if db:
        try:
            # Update data ke Firebase
            db.collection('products').document(id).update({
                "name": request.form.get('name'), 
                "tagline": request.form.get('tagline'),
                "price": int(request.form.get('price')), 
                "unit": request.form.get('unit'),
                "original_price": request.form.get('original_price'), 
                "prefix": request.form.get('prefix'),
                "image_url": request.form.get('image_url'), 
                "download_url": request.form.get('download_url'),
                "description": request.form.get('description')
            })
            print(f"✅ Sukses Update Produk: {id}")
        except Exception as e:
            print(f"❌ Gagal Update: {e}")
            return f"Gagal Update: {e}"

    return redirect('/admin') # Balik ke dashboard

# 👇 ROUTE BARU: CARI UID PAKAI EMAIL 👇
@app.route('/admin/find_uid', methods=['POST'])
def find_uid_by_email():
    # Cek Login Admin (Opsional, nyalakan kalau mau aman)
    # if not session.get('is_admin'): return jsonify({'success': False, 'message': 'Login dulu bos!'})

    email = request.form.get('email', '').strip()
    
    if not email:
        return jsonify({'success': False, 'message': 'Email kosong!'})

    try:
        # Cari user di database Auth Firebase
        user = auth.get_user_by_email(email)
        return jsonify({
            'success': True, 
            'uid': user.uid, 
            'message': f'✅ Ditemukan: {user.uid}'
        })
        
    except auth.UserNotFoundError:
        return jsonify({'success': False, 'message': '❌ User belum login/daftar di App!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# 👇 ROUTE PENGATURAN (HARGA & KONTAK) YANG KETINGGALAN 😂 👇

@app.route('/admin/settings', methods=['POST'])
def update_settings():
    # 🔒 Cek Tiket Admin (Biar aman)
    if not session.get('is_admin'): 
        return redirect('/login')
    
    if db:
        try:
            # 1. Simpan Info Kontak (Perusahaan, WA, Email, Alamat)
            db.collection('settings').document('contact').set({
                "company": request.form.get('company', ''), 
                "address": request.form.get('address', ''),
                "whatsapp": request.form.get('whatsapp', ''), 
                "email": request.form.get('email', '').strip()
            })
            
            # 2. Ambil input harga dari form HTML
            nexa_price = request.form.get('nexapos_price')
            mood_price = request.form.get('moodly_price')
            
            # 3. Simpan Harga Aplikasi (Pastikan jadi angka/integer)
            db.collection('settings').document('pricing').set({
                'nexapos_price': int(nexa_price) if nexa_price else 150000,
                'moodly_price': int(mood_price) if mood_price else 50000
            }, merge=True)
            
            flash("✅ Pengaturan Harga & Kontak Berhasil Disimpan!", "success")
            
        except Exception as e:
            print(f"❌ Error Simpan Settings: {e}")
            flash(f"❌ Gagal menyimpan: {e}", "error")

    # Balik lagi ke halaman admin setelah selesai
    return redirect('/admin')

# 👇 ROUTE HALAMAN PEMBAYARAN QRIS (YANG KETINGGALAN) 😂 👇

@app.route('/payment')
@app.route('/payment.html') # Jaga-jaga kalau Bos/User terbiasa ngetik .html
def payment_page():
    # Ambil data dari URL (kalau Bos mau ngasih link custom ke user)
    # Contoh link: logiclife.site/payment?product=Moodly
    product_name = request.args.get('product', 'Aplikasi Premium LogicLife')
    uid = request.args.get('uid', '')
    email = request.args.get('email', '')
    
    # Render tampilan payment.html yang isi QRIS tadi
    return render_template('payment.html', 
                           product_name=product_name, 
                           uid=uid, 
                           email=email)

# 👇 PINTU KHUSUS APLIKASI FLUTTER (BIAR GAK LOADING TERUS) 👇

@app.route('/api/get_pricing', methods=['GET'])
def get_pricing_api():
    # Tangkap parameter 'app_id' dari Flutter (moodly / nexapos)
    app_id = request.args.get('app_id', '')
    
    # 1. Siapkan harga default (Jaga-jaga kalau DB kosong)
    pricing_data = {
        "nexapos_price": 150000, 
        "moodly_price": 50000,
        "success": True
    }
    
    # 2. Ambil harga terbaru dari database (yang Bos atur di Admin)
    if db:
        try:
            doc = db.collection('settings').document('pricing').get()
            if doc.exists:
                db_prices = doc.to_dict()
                pricing_data.update(db_prices) # Timpa dengan harga dari DB
        except Exception as e:
            print(f"Error API Pricing: {e}")
            
    # 3. Sesuaikan respon 'price' utama biar Flutter gampang bacanya
    if app_id == 'moodly':
        pricing_data['price'] = pricing_data.get('moodly_price', 50000)
    elif app_id == 'nexapos':
        pricing_data['price'] = pricing_data.get('nexapos_price', 150000)
        
    # 4. Kirim balikan dalam format JSON
    return jsonify(pricing_data)

# 👇 PINTU CHECKOUT / TOMBOL BELI DARI APLIKASI 👇

@app.route('/buy_pro', methods=['GET', 'POST'])
def buy_pro_redirect():
    # 1. Tangkap data otomatis dari aplikasi Flutter
    uid = request.args.get('uid', '')
    email = request.args.get('email', '')
    app_id = request.args.get('app_id', '')
    
    # 2. Tentukan Nama Produk biar keren di halaman QRIS
    if app_id == 'moodly':
        product_name = 'Moodly Premium'
    elif app_id == 'nexapos':
        product_name = 'NexaPOS PRO'
    else:
        product_name = 'LogicLife Premium'
        
    # 3. Langsung buka halaman QRIS (payment.html)
    # Hebatnya: uid & email langsung kita oper ke HTML biar masuk ke tombol WA!
    return render_template('payment.html', 
                           product_name=product_name, 
                           uid=uid, 
                           email=email)


if __name__ == '__main__':
    app.run(debug=True)