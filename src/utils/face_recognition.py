import face_recognition
import numpy as np
from src.accounts.models import db, FaceRecognition
import os
import uuid
from src.accounts.models import db, FaceRecognition, User
UPLOAD_FOLDER = "static/uploads"  # Fotoğraflar için hedef klasör

def get_face_encoding(image_path):
    """Bu fonksiyon, verilen fotoğraftan yüz encoding verisini döndürür."""
    image = face_recognition.load_image_file(image_path)
    face_encodings = face_recognition.face_encodings(image)

    if len(face_encodings) == 0:
        print("Yüz bulunamadı!")
        return None
    elif len(face_encodings) > 1:
        print("Birden fazla yüz tespit edildi!")
        return None
    return face_encodings[0]

def check_face_exists(face_encoding, user_id=None):
    all_faces = FaceRecognition.query.all()
    
    for face in all_faces:
        # User tablosundan ilgili kullanıcıyı bul
        user = User.query.filter_by(face_id=face.id).first()
        
        if user_id and user and user.id == user_id:
            continue
            
        stored_encoding = np.frombuffer(face.encoding, dtype=np.float64)
        distance = face_recognition.face_distance([stored_encoding], face_encoding)[0]
        
        if distance < 0.5:
            return True
            
    return False

def save_face_encoding(face_encoding, photo_path):
    """Encoding verisini yüz tanıma modeline kaydeder ve face_id döndürür."""
    try:
        encoding_bytes = np.array(face_encoding, dtype=np.float64).tobytes()
        face_recognition_entry = FaceRecognition(encoding=encoding_bytes, image_path=photo_path)
        db.session.add(face_recognition_entry)
        db.session.commit()
        print(f"Face encoding saved with ID {face_recognition_entry.id}")
        return face_recognition_entry.id
    except ValueError as e:
        print(f"Encoding verisi kaydedilirken hata oluştu: {str(e)}")
        return None

def save_photo(photo):
    """Fotoğrafı rastgele isimle kaydeder ve dosya yolunu döndürür."""
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)  # Klasör yoksa oluştur
    ext = photo.filename.rsplit('.', 1)[1].lower()  # Uzantıyı al
    filename = f"{uuid.uuid4().hex}.{ext}"  # Rastgele bir isim oluştur
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    photo.save(file_path)
    return file_path