from flask import Flask
import os
from routes import routes
from utils.dbconn import mysql

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Your mysql root password'
app.config['MYSQL_DB'] = 'flaskdev'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql.init_app(app)

app.register_blueprint(routes)

if __name__ == '__main__':
    app.run(debug=True)
