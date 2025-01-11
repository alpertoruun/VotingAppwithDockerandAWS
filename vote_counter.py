#!/usr/bin/env python3
import sys
import os
from datetime import datetime

print("Script başlatıldı")

# Mevcut dizin ve path bilgilerini yazdır
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Mevcut dizin: {current_dir}")
print(f"Python Path: {sys.path}")
sys.path.append(current_dir)
print(f"Güncellenmiş Python Path: {sys.path}")

try:
    print("src import öncesi")
    from src import app
    print("src import sonrası")
    from src.utils.count_votes_utils import count_votes
    print("count_votes import edildi")
except Exception as e:
    print(f"Import sırasında hata: {str(e)}")
    sys.exit(1)

def main():
    with app.app_context():
        try:
            print(f"Oy sayım işlemi başlatılıyor - {datetime.now()}")
            count_votes()
            print("Oy sayım işlemi başarıyla tamamlandı")
        except Exception as e:
            print(f"Oy sayım sırasında hata oluştu: {str(e)}")

if __name__ == "__main__":
    try:
        print("main() fonksiyonu çağrılıyor")
        main()
        print("main() fonksiyonu tamamlandı")
    except Exception as e:
        print(f"Ana programda hata: {str(e)}")