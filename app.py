from tensorflow.keras.models import load_model
from tensorflow.keras.models import model_from_json
from PIL import Image
from PIL import Image
import numpy as np
import os
import cv2
from flask import Flask, render_template, url_for, request, redirect, flash, abort, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import random
import urllib.request
import os
import glob

#loading models
json_file = open('static/ml/model.json', 'r')
loaded_model_json = json_file.read()
json_file.close()
loaded_model = model_from_json(loaded_model_json)
loaded_model.load_weights("static/ml/model.h5")

#Creating function to convert input img to np array
def convert(img):
    img1 = cv2.imread(img)
    img = Image.fromarray(img1, 'RGB')
    image = img.resize((50, 50))
    return (np.array(image))

#Creating function to analyze cell label and return Paractized or Uninfected
def cell_name(label):
    if label == 0:
        return ("Positive")
    if label == 1:
        return ("Negative")

#Creating function to perform all analysis on input image, including running it through the other functions
def predict(file):
    ar = convert(file)
    ar = ar/255
    label = 1
    a = []
    a.append(ar)
    a = np.array(a)
    score = loaded_model.predict(a, verbose=1)
    label_index=np.argmax(score)
    acc=np.max(score)
    print(acc)
    Cell=cell_name(label_index)
    return Cell.lower()

def validate_image(stream):
    header = stream.read(512)  # 512 bytes should be enough for a header check
    stream.seek(0)  # reset stream pointer
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')

def emptyFolder(filePath):
  files = glob.glob(filePath)
  for f in files:
    os.remove(f)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///images.db'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.gif']
app.config['UPLOAD_PATH'] = 'uploads'
db = SQLAlchemy(app)

class FileContents(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(300))
  data = db.Column(db.LargeBinary)
  result = db.Column(db.String(300))
  data_created = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/home/result:<result>')
def result(result):
  data = FileContents.query.order_by(FileContents.data_created).all()
  return render_template('result.html', r=result, data=data)

@app.route("/home", methods=['POST', 'GET'])
def home():
  if request.method == 'POST':
    uploaded_file = request.files['img']
    filename = uploaded_file.filename
    if filename != '':
      file_ext = os.path.splitext(filename)[1]
      if (file_ext not in app.config['UPLOAD_EXTENSIONS']):
        abort(400)
      uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))

    result = predict("uploads/" + filename)
    print(result)
    newFile = FileContents(name=filename, data=uploaded_file.read(), result=result)
    db.session.add(newFile)
    db.session.commit()

    return redirect(url_for('result', result=result.capitalize()))
  else:
    data = FileContents.query.order_by(FileContents.data_created).all()
    return render_template('index.html', r="Please submit an image", data=data)

@app.route("/delete/<int:id>")
def delete(id):
  data_to_delete = FileContents.query.get_or_404(id)

  try:
    db.session.delete(data_to_delete)
    db.session.commit()
    return redirect(url_for('home'))
  except:
    return '<h1>There was a problem deleting that data</h1>'


@app.route("/")
def login():
  return render_template("login.html")

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
