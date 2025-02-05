from flask import Flask
import json
import mysql.connector
from mysql.connector import pooling, errorcode


def create_app():
    app = Flask(__name__)

    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config.update(
        SESSION_COOKIE_SAMESITE='Lax'
    )
    app.secret_key = b'U\xfc\x92"DGw\xff\xcfG\x06\x90\xe7\x9d\x9d\xc7~\xee\xe3\xf1\xc2\xb8\xcb\xa5'

    from website.auth import auth 
    from website.views import views 

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    tiedosto = open("dbconfig.json", encoding="UTF-8")
    dbconfig = json.load(tiedosto)

    # luodaan MySql pooling
    try:
        app.pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="tietokantayhteydet",
            pool_size=2,  
            autocommit=True,
            charset='utf8mb4',
            **dbconfig
        )
        print("Connection pool created successfully.")
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Invalid username or password.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist.")
        else:
            print(err)   

    return app
