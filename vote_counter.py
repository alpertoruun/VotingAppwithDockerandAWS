#!/usr/bin/env python3
import sys
import os
from datetime import datetime
import logging

logging.basicConfig(
    filename='vote_counter.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src import app
from src.utils.count_votes_utils import count_votes

def main():
    with app.app_context():
        try:
            logging.info(f"Oy sayım işlemi başlatılıyor - {datetime.now()}")
            count_votes()
            logging.info("Oy sayım işlemi başarıyla tamamlandı")
        except Exception as e:
            logging.error(f"Oy sayım sırasında hata oluştu: {str(e)}")

if __name__ == "__main__":
    main()