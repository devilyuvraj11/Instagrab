from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os, tempfile, shutil, re
from yt_dlp import YoutubeDL
import validators

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app, resources={r"/*": {"origins": "*"}})

# -------------------- URL VALIDATION --------------------

def is_instagram_url(url: str) -> bool:
    if not validators.url(url):
        return False
    return re.search(r"(instagram\.com/(reel|p|tv|stories))", url, re.IGNORECASE)

def is_facebook_url(url: str) -> bool:
    if not validators.url(url):
        return False
    return re.search(r"(facebook\.com|fb\.watch)", url, re.IGNORECASE)

# -------------------- STATIC FILES --------------------

@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(".", "sitemap.xml", mimetype="application/xml")

@app.route("/robots.txt")
def robots():
    return send_from_directory(".", "robots.txt", mimetype="text/plain")

# -------------------- PAGES --------------------

@app.route("/")
@app.route("/instagram")
def instagram():
    return render_template("index.html")

@app.route("/facebook")
def facebook():
    return render_template("facebook.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/privacy-policy")
def privacy():
    return render_template("privacy-policy.html")

# -------------------- GLOBAL ERROR HANDLER --------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"detail": "Invalid request"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"detail": "Server error"}), 500

# -------------------- COOKIES --------------------

COOKIES_FILE = os.path.join(os.getcwd(), 'cookies.txt')
USE_COOKIES = os.path.exists(COOKIES_FILE)

def build_ydl_opts(tmpdir):
    opts = {
        'outtmpl': os.path.join(tmpdir, '%(title)s-%(id)s.%(ext)s'),
        'format': 'bv*+ba/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'noprogress': True,
        'retries': 3,
        'fragment_retries': 3,
        'nocheckcertificate': True,
    }
    if USE_COOKIES:
        opts['cookiefile'] = COOKIES_FILE
    return opts

# -------------------- PREVIEW --------------------

@app.route('/preview', methods=['GET'])
def preview():
    post_url = request.args.get('url', '').strip()
    if not post_url:
        return jsonify({'detail': 'Enter valid link'}), 400

    # Detect which page requested preview
    source = request.args.get("source", "instagram")

    if source == "instagram" and not is_instagram_url(post_url):
        return jsonify({'detail': 'Only Instagram links allowed'}), 400

    if source == "facebook" and not is_facebook_url(post_url):
        return jsonify({'detail': 'Only Facebook links allowed'}), 400

    tmpdir = tempfile.mkdtemp(prefix='ytdl-preview-')
    try:
        opts = build_ydl_opts(tmpdir)
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(post_url, download=False)

        formats = info.get('formats') or []
        best_url = None
        best_score = -1

        for f in formats:
            if f.get('url'):
                score = f.get('height') or f.get('tbr') or 0
                if score > best_score:
                    best_score = score
                    best_url = f['url']

        if not best_url:
            best_url = info.get('url')

        if not best_url:
            return jsonify({'detail': 'No media URL found'}), 404

        return jsonify({'resolved_url': best_url}), 200

    except Exception:
        return jsonify({'detail': 'Enter valid link'}), 400
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# -------------------- INSTAGRAM DOWNLOAD --------------------

@app.route('/download', methods=['POST'])
def download_instagram():
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'detail': 'Enter Instagram link'}), 400

    if not is_instagram_url(url):
        return jsonify({'detail': 'Instagram links only allowed'}), 400

    return process_download(url)

# -------------------- FACEBOOK DOWNLOAD --------------------

@app.route('/facebook/download', methods=['POST'])
def download_facebook():
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'detail': 'Enter Facebook link'}), 400

    if not is_facebook_url(url):
        return jsonify({'detail': 'Facebook links only allowed'}), 400

    return process_download(url)

# -------------------- COMMON DOWNLOAD ENGINE --------------------

def process_download(post_url):
    tmpdir = tempfile.mkdtemp(prefix='dl-')

    try:
        opts = build_ydl_opts(tmpdir)
        with YoutubeDL(opts) as ydl:
            ydl.extract_info(post_url, download=True)

        files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
        if not files:
            return jsonify({'detail': 'Download failed'}), 500

        files.sort(key=lambda p: os.path.getsize(p), reverse=True)
        filepath = files[0]

        return send_file(
            filepath,
            as_attachment=True,
            download_name=os.path.basename(filepath),
            mimetype='video/mp4'
        )

    except Exception as e:
        return jsonify({'detail': 'Download error', 'error': str(e)}), 500

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# --------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
