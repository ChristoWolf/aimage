from flask import *
from werkzeug.utils import secure_filename
import os
import uuid


# TODO: use appropriate responses (e.g. JSON, HTML, binary) at fitting places
# TODO: change request handling to make more sense (e.g. GET on image endpoint should give related links instead of data)
class RestAPI:
    def __init__(self, port, uploadFolder):
        self.app = Flask(__name__)
        self.port = port
        self.app.config["UPLOAD_FOLDER"] = uploadFolder  # TODO: check if folder makes sense
        self.allowedExtensions = set(['png', 'jpg', 'jpeg'])  # extend allowed extensions
        self.app.url_map.strict_slashes = False
        self.__defineRESTAPI()

    def runRestAPI(self):
        self.app.run(host="localhost", port=self.port)

    def __defineRESTAPI(self):
        @self.app.route("/", methods=["GET"])
        def render_home():
            return render_template("home.html")

        @self.app.route("/images/<filename>", methods=["GET"])
        def imagesEndpointGetSingle(filename):
            return send_from_directory(self.app.config["UPLOAD_FOLDER"], filename + ".png")

        @self.app.route("/images/<filename>", methods=["DELETE"])
        def imagesEndpointDeleteSingle(filename):
            fileName = secure_filename(filename)
            if not os.path.isdir(self.app.config['UPLOAD_FOLDER']):
                os.makedirs(self.app.config['UPLOAD_FOLDER'])
                abort(404)
            if not os.path.exists(os.path.join(self.app.config['UPLOAD_FOLDER'], fileName + ".png")):
                abort(404)
            os.remove(os.path.join(self.app.config['UPLOAD_FOLDER'], fileName + ".png"))
            if os.path.exists(os.path.join(self.app.config['UPLOAD_FOLDER'], fileName + ".png")):
                abort(500)
            return "Image deleted successfully!"

        @self.app.route("/images", methods=["POST"])
        def imagesEndpointPostSingle():
            if request.data == b"":
                abort(400)
            if not self.__isImageTypeAllowed(request.content_type):
                abort(416)
            fileName = str(uuid.uuid4()).replace("-", "")
            if not os.path.isdir(self.app.config['UPLOAD_FOLDER']):
                os.makedirs(self.app.config['UPLOAD_FOLDER'])
            elif os.path.exists(os.path.join(self.app.config['UPLOAD_FOLDER'], fileName + ".png")):
                abort(409)  # TODO: generate new ID instead
            with open(os.path.join(self.app.config['UPLOAD_FOLDER'], fileName + ".png"), "wb") as file:
                file.write(request.data)
            return make_response("Image uploaded successfully!\nID: " + fileName, 201)

        @self.app.route("/images", methods=["GET"])
        def imagesEndpointGetCollection():
            images = [image.replace(".png", "") for image in os.listdir(self.app.config['UPLOAD_FOLDER'])
                      if os.path.isfile(os.path.join(self.app.config['UPLOAD_FOLDER'], image))
                      and image.rsplit(".", 1)[1] == "png"]
            if not images:
                return ""
            return "\n".join(images)

        @self.app.route("/images/<filename>/metadata", methods=["GET"])
        def imagesEndpointGetMetadata(filename):
            if not os.path.exists(os.path.join(self.app.config['UPLOAD_FOLDER'], filename + ".png")):
                abort(404)
            return filename

        @self.app.route("/images/<filename>/data", methods=["GET"])
        def imagesEndpointGetData(filename):
            if not os.path.exists(os.path.join(self.app.config['UPLOAD_FOLDER'], filename + ".png")):
                abort(404)
            return send_from_directory(self.app.config["UPLOAD_FOLDER"], filename + ".png")


    def __isImageTypeAllowed(self, contentType):
        split = contentType.rsplit("/", 1)
        return split[0] == "image" and split[1] in self.allowedExtensions