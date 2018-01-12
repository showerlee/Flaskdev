from flask import Flask
import os
from routes import routes
from utils.dbconn import mysql
from flask_uploads import configure_uploads, patch_request_class
from utils.upload import photos

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'your mysql root password'
app.config['MYSQL_DB'] = 'flaskdev'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql.init_app(app)

app.config['UPLOADED_PHOTOS_DEST'] = 'static/avatar'
configure_uploads(app, photos)
patch_request_class(app)  # set maximum file size, default is 16MB

app.register_blueprint(routes)


if __name__ == '__main__':
    app.run(debug=True)
