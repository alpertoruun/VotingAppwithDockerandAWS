from src import db, app
from src.accounts.models import *  # Tüm modelleri içe aktar

with app.app_context():
    print("Veritabanı tabloları oluşturuluyor...")
    db.create_all()
    print("Veritabanı tabloları başarıyla oluşturuldu.")
