from flask import *
from flasgger import Swagger
from werkzeug.utils import secure_filename
from functools import wraps
import os
import uuid


# TODO: outsource schemas to JSON files and reference them remotely, see https://swagger.io/docs/specification/using-ref (Remote Reference)
# TODO: improve hyphen-replacement  for UUIDs (i.e. keep UUID-formats in mind)
# TODO: use appropriate responses (e.g. JSON, HTML, binary) at fitting places
# TODO: use a DB to persistently save credentials and metadata (see e.g. https://docs.python.org/3/library/sqlite3.html)
class RestAPI:
    def __init__(self, port, uploadFolder):
        self.app = Flask(__name__)
        self.port = port
        self.app.config["UPLOAD_FOLDER"] = uploadFolder  # TODO: check if folder makes sense
        self.allowedExtensions = set(['png', 'jpg', 'jpeg'])  # extend allowed extensions
        self.app.url_map.strict_slashes = False
        self.swagger_config = {
            "version": "0.0.1",
            "uiversion": 3,  # needed to use OpenAPI spec
            "openapi": "3.0.2",  # needed to use OpenAPI spec
            "title": "AImage REST API Documentation",
            "headers": [
            ],
            "specs": [
                {
                    "endpoint": 'api_v1',
                    "route": '/api_v1.json',
                    "rule_filter": lambda rule: True,  # all in
                    "model_filter": lambda tag: True,  # all in
                }
            ],
            "static_url_path": "/flasgger_static",
            # "static_folder": "static",  # must be set by user
            "swagger_ui": True,
            "specs_route": "/api/"
        }
        # TODO: try to put security usage in here
        self.swagger_template = {
            'components': {
                'securitySchemes': {
                    'basicAuth': {
                        'type': 'http',
                        'scheme': 'basic'
                    }
                }
            }
        }
        self.api_doc = Swagger(self.app, self.swagger_config, None, self.swagger_template)
        self.__defineRESTAPI()

    def runRestAPI(self):
        self.app.run(host="0.0.0.0", port=self.port)

    def __defineRESTAPI(self):
        def check_auth(username, password):
            return username == "testuser" and password == "begonethot"

        # wrapper used to decorate functions which require authentication
        def requires_auth(function):
            @wraps(function)
            def decorated(*args, **kwargs):
                auth = request.authorization
                if not auth or not check_auth(auth.username, auth.password):
                    abort(401)
                return function(*args, **kwargs)
            return decorated

        @self.app.route("/")
        def render_home():
            url = request.host_url
            return render_template("home.html").replace("$URL$", url + "api/")

        @self.app.route("/images/<image_id>", methods=["GET"])
        @requires_auth
        def imagesEndpointGetSingle(image_id):
            """
            Get the specified image resource.
            ---
            tags:
                - GET
            parameters:
                - name: image_id
                  in: path
                  description: UUID of an image resource.
                  required: true
                  schema:
                    type: string
            responses:
                '200':
                    description: Returns the requested image resource.
                    content:
                        application/json:
                            schema:
                                type: object
                                properties:
                                    image_id:
                                        type: string
                                        description: UUID of the image resource.
                                        example: CB8BC8406ED14386BC4962A719B17F69
                                    links:
                                        type: object
                                        description: Collection of links related to this resource.
                                        properties:
                                            self:
                                                type: object
                                                properties:
                                                    href:
                                                        type: string
                                                        example: http://host:port/images/CB8BC8406ED14386BC4962A719B17F69
                                                    templates:
                                                        type: object
                                                        properties:
                                                            GET:
                                                                type: object
                                                            DELETE:
                                                                type: object
                                            up:
                                                type: object
                                                properties:
                                                    href:
                                                        type: string
                                                        example: http://host:port/images
                                                    templates:
                                                        type: object
                                                        properties:
                                                            GET:
                                                                type: object
                                                            POST:
                                                                type: object
                                            metadata:
                                                type: object
                                                properties:
                                                    href:
                                                        type: string
                                                        example: http://host:port/images/CB8BC8406ED14386BC4962A719B17F69/metadata
                                                    templates:
                                                        type: object
                                                        properties:
                                                            GET:
                                                                type: object
                                            data:
                                                type: object
                                                properties:
                                                    href:
                                                        type: string
                                                        example: http://host:port/images/CB8BC8406ED14386BC4962A719B17F69/data
                                                    templates:
                                                        type: object
                                                        properties:
                                                            GET:
                                                                type: object

            security:
                - basicAuth: []
            """
            # TODO: change logic to give JSON response as defined above
            return send_from_directory(self.app.config["UPLOAD_FOLDER"], image_id.replace("-", "").upper() + ".png")

        @self.app.route("/images/<image_id>", methods=["DELETE"])
        @requires_auth
        def imagesEndpointDeleteSingle(image_id):
            fileName = secure_filename(image_id.replace("-", "").upper())
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
        @requires_auth
        def imagesEndpointPostSingle():
            if request.data == b"":
                abort(400)
            if not self.__isImageTypeAllowed(request.content_type):
                abort(416)
            fileName = str(uuid.uuid4()).replace("-", "").upper()
            if not os.path.isdir(self.app.config['UPLOAD_FOLDER']):
                os.makedirs(self.app.config['UPLOAD_FOLDER'])
            elif os.path.exists(os.path.join(self.app.config['UPLOAD_FOLDER'], fileName + ".png")):
                abort(409)  # TODO: generate new ID instead
            with open(os.path.join(self.app.config['UPLOAD_FOLDER'], fileName + ".png"), "wb") as file:
                file.write(request.data)
            return make_response("Image uploaded successfully!\nID: " + fileName, 201)

        @self.app.route("/images", methods=["GET"])
        @requires_auth
        def imagesEndpointGetCollection():
            images = [image.replace(".png", "") for image in os.listdir(self.app.config['UPLOAD_FOLDER'])
                      if os.path.isfile(os.path.join(self.app.config['UPLOAD_FOLDER'], image))
                      and image.rsplit(".", 1)[1] == "png"]
            if not images:
                return ""
            return "\n".join(images)

        @self.app.route("/images/<image_id>/metadata", methods=["GET"])
        @requires_auth
        def imagesEndpointGetMetadata(image_id):
            image_id = image_id.replace("-", "").upper()
            if not os.path.exists(os.path.join(self.app.config['UPLOAD_FOLDER'], image_id + ".png")):
                abort(404)
            return image_id

        @self.app.route("/images/<image_id>/data", methods=["GET"])
        @requires_auth
        def imagesEndpointGetData(image_id):
            image_id = image_id.replace("-", "").upper()
            if not os.path.exists(os.path.join(self.app.config['UPLOAD_FOLDER'], image_id + ".png")):
                abort(404)
            return send_from_directory(self.app.config["UPLOAD_FOLDER"], image_id + ".png")


    def __isImageTypeAllowed(self, contentType):
        split = contentType.rsplit("/", 1)
        return split[0] == "image" and split[1] in self.allowedExtensions
