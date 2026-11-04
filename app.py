from flask import Flask, render_template
from routes.upload_routes import upload_bp
from routes.analysis_routes import analysis_bp
from routes.recommendations_routes import recommendations_bp
from routes.cleaning_routes import cleaning_bp

app = Flask(__name__)
app.secret_key = "dataqual-local-development-key"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.register_blueprint(upload_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(recommendations_bp)
app.register_blueprint(cleaning_bp)

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.errorhandler(413)
def file_too_large(_error):
    return {"error": "File is too large. Maximum upload size is 16 MB."}, 413

if __name__ == "__main__":
    app.run(debug=True)
