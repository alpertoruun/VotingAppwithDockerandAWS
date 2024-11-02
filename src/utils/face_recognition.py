import face_recognition
import numpy as np
from src.accounts.models import db, FaceRecognition

def get_face_encoding(image_path):
    """Bu fonksiyon, verilen fotoğraftan yüz encoding verisini döndürür."""
    image = face_recognition.load_image_file(image_path)
    face_encodings = face_recognition.face_encodings(image)

    if len(face_encodings) == 0:
        print("Yüz bulunamadı!")
        return None
    return face_encodings[0]

def save_face_encoding(face_encoding):
    """Encoding verisini yüz tanıma modeline kaydeder ve face_id döndürür."""
    try:
        encoding_bytes = np.array(face_encoding, dtype=np.float64).tobytes()
        face_recognition_entry = FaceRecognition(encoding=encoding_bytes)
        db.session.add(face_recognition_entry)
        db.session.commit()
        print(f"Face encoding saved with ID {face_recognition_entry.id}")
        return face_recognition_entry.id
    except ValueError as e:
        print(f"Encoding verisi kaydedilirken hata oluştu: {str(e)}")
        return None