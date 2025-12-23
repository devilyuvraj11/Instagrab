from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, Response
from flask_cors import CORS
import os, tempfile, shutil, uuid, traceback
from yt_dlp import YoutubeDL

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(".", "sitemap.xml", mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    return send_from_directory(".", "robots.txt", mimetype="text/plain")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/privacy-policy")
def privacy():
    return render_template("privacy-policy.html")


# If you want to support downloading private posts, place a cookies.txt
# (Netscape format) in the project root and yt-dlp will use it.
COOKIES_FILE = os.path.join(os.getcwd(), 'cookies.txt')
USE_COOKIES = os.path.exists(COOKIES_FILE)

def build_ydl_opts(tmpdir):
    opts = {
        'outtmpl': os.path.join(tmpdir, '%(title)s-%(id)s.%(ext)s'),
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
    }
    if USE_COOKIES:
        opts['cookiefile'] = COOKIES_FILE
    return opts

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/preview', methods=['GET'])
def preview():
    """
    Return a JSON with a direct streamable URL (if possible) for preview.
    Uses yt-dlp extract_info(download=False) to get usable format URL.
    """
    post_url = request.args.get('url', '').strip()
    if not post_url:
        return jsonify({'detail': 'Missing url parameter'}), 400

    tmpdir = tempfile.mkdtemp(prefix='ytdl-preview-')
    try:
        opts = build_ydl_opts(tmpdir)
        with YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(post_url, download=False)
            except Exception as e:
                return jsonify({'detail': 'yt-dlp error', 'error': str(e)}), 500

        # If direct url available in info, try to pick a good format
        formats = info.get('formats') or []
        # prefer best format with direct URL
        best_url = None
        best_score = -1
        for f in formats:
            url = f.get('url')
            if not url:
                continue
            # score by height or bitrate
            score = f.get('height') or f.get('tbr') or 0
            if score > best_score:
                best_score = score
                best_url = url
        # fallback to info.get('url')
        if not best_url:
            best_url = info.get('url')

        if not best_url:
            return jsonify({'detail': 'Could not get direct media URL from yt-dlp info'}), 404

        # return the direct URL (note: some hosts require headers/cookies; browser may still block CORS)
        return jsonify({'resolved_url': best_url, 'title': info.get('title'), 'uploader': info.get('uploader')}), 200
    finally:
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

@app.route('/download', methods=['POST'])
def download():
    """
    Use yt-dlp to download the post to a temporary file, then return it with send_file().
    The frontend expects a streamed response and will show preview first via /preview.
    """
    data = request.get_json(silent=True) or {}
    post_url = data.get('url', '').strip()
    if not post_url:
        return jsonify({'detail': 'Missing url in request body'}), 400

    tmpdir = tempfile.mkdtemp(prefix='ytdl-dl-')
    try:
        opts = build_ydl_opts(tmpdir)
        # enable progress and verbose on error for debugging if needed
        with YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(post_url, download=True)
            except Exception as e:
                # include traceback for debugging
                tb = traceback.format_exc()
                return jsonify({'detail': 'yt-dlp download error', 'error': str(e), 'trace': tb}), 500

        # find the downloaded file
        files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
        if not files:
            return jsonify({'detail': 'No file produced by yt-dlp'}), 500
        # pick the largest file (likely merged mp4)
        files.sort(key=lambda p: os.path.getsize(p), reverse=True)
        filepath = files[0]
        filename = os.path.basename(filepath)

        # send file as attachment (Flask will stream it)
        return send_file(filepath, as_attachment=True, download_name=filename, mimetype='video/mp4')
    finally:
        # cleanup temporary directory after request finishes — Flask send_file will have opened file
        # schedule removal: try remove after a short delay when safe; for simplicity remove synchronously
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

if __name__ == '__main__':
    # dev server
    app.run(host='0.0.0.0', port=8000, debug=False)
