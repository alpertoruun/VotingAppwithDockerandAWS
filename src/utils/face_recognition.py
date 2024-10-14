import face_recognition
import numpy as np
from models import session, FaceRecognition

def save_face_encoding(image_path, voter_id):
    image = face_recognition.load_image_file(image_path)
    face_encodings = face_recognition.face_encodings(image)

    if len(face_encodings) == 0:
        print("No face found!")
        return False

    face_encoding = face_encodings[0]
    encoding_bytes = np.array(face_encoding).tobytes()

    face_recognition_entry = FaceRecognition(
        voter_id=voter_id,
        encoding=encoding_bytes
    )

    session.add(face_recognition_entry)
    session.commit()
    print(f"Face encoding saved for Voter ID {voter_id}")

def compare_face_with_database():
    video_capture = cv2.VideoCapture(0)
    face_data = session.query(FaceRecognition).all()

    known_face_encodings = [np.frombuffer(face.encoding) for face in face_data]
    print("Loaded all face data from the database.")

    while True:
        ret, frame = video_capture.read()
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)

            if True in matches:
                print("Face matched!")
            else:
                print("No match!")

        if cv2.waitKey(1) & 0xFF == 27:
            break

    video_capture.release()
    cv2.destroyAllWindows()

save_face_encoding("./alp.jpeg", voter_id=1)

compare_face_with_database()