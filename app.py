from flask import Flask, render_template, Response, request, jsonify
import cv2
import face_recognition
import numpy as np
import mysql.connector
import datetime
import base64
import os

app = Flask(__name__)
video_capture = None
camera_url = ""

# --- Connexion à la base ---
def get_known_faces():
    conn = mysql.connector.connect(
        host="mainline.proxy.rlwy.net", user="root", password="gEhDoQVyDBPAQdkPKRplGXIjJOLJMzKI", database="railway" , port=37978
    )
    cursor = conn.cursor()
    cursor.execute("SELECT nom, image FROM visages")

    known_encodings = []
    known_names = []

    for nom, img_blob in cursor.fetchall():
        nparr = np.frombuffer(img_blob, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        enc = face_recognition.face_encodings(rgb_img)
        if enc:
            known_encodings.append(enc[0])
            known_names.append(nom)

    cursor.close()
    conn.close()
    return known_encodings, known_names

known_encodings, known_names = get_known_faces()

# --- Enregistrement dans journal_detection ---
def enregistrer_detection(nom, frame):
    try:
        _, img_encoded = cv2.imencode('.jpg', frame)
        img_blob = img_encoded.tobytes()

        conn = mysql.connector.connect(
           host="mainline.proxy.rlwy.net", user="root", password="gEhDoQVyDBPAQdkPKRplGXIjJOLJMzKI", database="railway" , port=37978
        )
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO journal_detection (nom, image, date_detection) VALUES (%s, %s, %s)",
            (nom, img_blob, datetime.datetime.now())
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Erreur insertion DB:", e)

# --- Route page d'accueil ---
@app.route('/')
def index():
    return render_template('dashboard.html')

# --- Lancement caméra IP ---
@app.route('/start_camera', methods=['POST'])
def start_camera():
    global video_capture, camera_url
    data = request.get_json()
    camera_url = data.get("url")
    video_capture = cv2.VideoCapture(camera_url)
    if not video_capture.isOpened():
        return jsonify({'error': 'Impossible d’ouvrir la caméra'}), 400
    return jsonify({'message': 'Caméra connectée'}), 200

# --- Génération du flux vidéo ---
def gen_frames():
    global video_capture
    found_faces = set()

    while True:
        success, frame = video_capture.read()
        if not success:
            break

        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small = small_frame[:, :, ::-1]

        face_locations = face_recognition.face_locations(rgb_small)
        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(known_encodings, face_encoding)
            name = "Inconnu"
            color = (0, 0, 255)

            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            if face_distances.any():
                best_match = np.argmin(face_distances)
                if matches[best_match]:
                    name = known_names[best_match]
                    color = (0, 255, 0)
                    if name not in found_faces:
                        print(f"🔔 {name} détecté !")
                        enregistrer_detection(name, frame)  # ⬅️ Enregistrement
                        found_faces.add(name)

            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# --- Flux vidéo MJPEG ---
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/suivi')
def suivi():
    conn = mysql.connector.connect(
        host="mainline.proxy.rlwy.net", user="root", password="gEhDoQVyDBPAQdkPKRplGXIjJOLJMzKI", database="railway" , port=37978
    )
    cursor = conn.cursor()
    cursor.execute("SELECT nom, image, date_detection FROM journal_detection ORDER BY date_detection DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    detections = []
    for nom, img_blob, date in rows:
        img_base64 = base64.b64encode(img_blob).decode('utf-8')
        detections.append({
            'nom': nom,
            'image': img_base64,
            'date': date.strftime('%Y-%m-%d %H:%M:%S')
        })

    return render_template('suivi.html', detections=detections)

# --- Lancer serveur ---


if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 5000))
    except (ValueError, TypeError):
        port = 5000
    app.run(host="0.0.0.0", port=port)
