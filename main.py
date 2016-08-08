import logging
import config
from flask import Flask
import uorm.sqlite 
import rating
import uauth

db_file = config.PROJECT_ID
if __name__ == '__main__':
	db_file += ".devel"
db_file += ".sqlite"

uorm.sqlite.connect(db_file, namespace="nuvola")

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
uauth.add_admin(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)
app.register_blueprint(rating.blueprint)
app.register_blueprint(uauth.blueprint)

@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

    
