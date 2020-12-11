from flask import Flask, request, abort, render_template, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os
import uuid
import atexit
import jsonpickle
import threading
import commands

UPLOAD_FOLDER = './pointclouds'
ALLOWED_EXTENSIONS = {'las', 'pcd'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = "super secret!"

POINTCLOUDS = {}

class ProcessingStage:
    def __init__(self, name, command, delta):
        self.name = name
        self.state = ""
        self.command = command
        self.delta = delta

class Pointcloud:
    def __init__(self, uid, name, filename):
        self.uid = uid
        self.name = name
        self.filename = filename

        self.complete = False
        self.progress = 0
        self.stages = [
            ProcessingStage("To PCD", commands.to_pcd, 10),
            ProcessingStage("Deleting ground", commands.remove_ground, 80),
            ProcessingStage("To LAS", commands.to_las, 10)
        ]
    
    def mark_complete(self, success = True):
        self.complete = True
        if success:
            self.progress = 100
            for s in self.stages:
                s.state = "success"

    def istype(self, extension):
        assert extension.startswith(".")
        return self.filename.endswith(extension)

    @property
    def las_filename(self):
        if self.istype(".las"):
            return self.filename
        elif self.istype(".pcd"):
            return self.filename[:-4] + ".las"
        else: # HACK manually crash program with appropriate error message (should never happen)
            assert False, "File extension of filename {} not allowed!".format(self.filename)
    @property
    def las_path(self):
        return "pointclouds/{}".format(self.las_filename)

    @property
    def pcd_filename(self):
        if self.istype(".pcd"):
            return self.filename
        elif self.istype(".las"):
            return self.filename[:-4] + ".pcd"
        else: # HACK manually crash program with appropriate error message (should never happen)
            assert False, "File extension of filename {} not allowed!".format(self.filename)
    @property
    def pcd_path(self):
        return "pointclouds/{}".format(self.pcd_filename)

@app.route('/')
def home():
    return render_template("index.html", pointclouds=POINTCLOUDS.values())

@app.route('/delete')
def delete_all():
    import shutil
    shutil.rmtree('pointclouds')
    os.makedirs('pointclouds')
    POINTCLOUDS.clear()
    return redirect(url_for('home'))

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
    def _call(stage):
        stage.state = "working"
        ret = stage.command(pointcloud)
        if ret:
            stage.state = "success"
        else:
            stage.state = "error"
            pointcloud.mark_complete(success=False)
        return ret

    for stage in pointcloud.stages:
        if not _call(stage):
            print("Error on stage {}".format(stage.name))
            return
        pointcloud.progress += stage.delta
    
    pointcloud.mark_complete()

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
            saved_file = "{}_{}".format(uid, filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_file))
            POINTCLOUDS[uid] = Pointcloud(uid=uid, name=request.form["title"], filename=saved_file)
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
