from flask import Flask, request, abort, render_template, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os
import uuid
import atexit
import jsonpickle
import threading


UPLOAD_FOLDER = './pointclouds'
ALLOWED_EXTENSIONS = {'las', 'pcd'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = "super secret!"

POINTCLOUDS = {}

class Pointcloud:
    def __init__(self, uid, name):
        self.complete = False
        self.uid = uid
        self.name = name

@app.route('/')
def home():
    return render_template("index.html", pointclouds=POINTCLOUDS.values())

@app.route("/cloud/<uid>")
def pc_details(uid):
    if not POINTCLOUDS.get(uid):
        abort(404)
    return render_template("details.html", pc=POINTCLOUDS[uid])
    
@app.route("/cloud/<uid>/original")
def pc_original(uid):
    if not POINTCLOUDS.get(uid):
        abort(404)
    return uid

@app.route("/cloud/<uid>/segmented")
def pc_segmented(uid):
    if not POINTCLOUDS.get(uid):
        abort(404)
    return uid

# Straight from https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def do_work(pointcloud):
    print("Working...")
    # TODO actually call executables!
    pointcloud.complete = True

@app.route('/upload', methods=['POST', 'GET'])
def upload_pointcloud():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        f = request.files['file']
        if f.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if f and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            uid = str(uuid.uuid4())
            if not os.path.isdir(app.config['UPLOAD_FOLDER']): # Create upload folder if required
                os.mkdir(app.config['UPLOAD_FOLDER'])
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], "{}_{}".format(uid, filename)))
            POINTCLOUDS[uid] = Pointcloud(uid=uid, name=request.form["title"])
            # spawn & kick off worker thread
            worker = threading.Thread(target=do_work, args=(POINTCLOUDS[uid],))
            worker.start()
            return redirect(url_for('pc_details', uid=uid))
    return render_template("upload.html")

def _save_data():
    # dump POINTCLOUDS to data.json
    with open("data.json", "w") as f:
        f.write(jsonpickle.encode(POINTCLOUDS))

if __name__ == "__main__":
    # populate POINTCLOUDS, if there is a JSON file saved on disk
    try:
        with open("data.json") as f:
            POINTCLOUDS = jsonpickle.decode(f.read())
    except IOError: # file didn't exist, no need to do anything (default is {} anyways)
        pass
        
    # Dump data to JSON file when exiting
    atexit.register(_save_data)

    app.run()
