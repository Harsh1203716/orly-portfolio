"""Orly's site server: serves the portfolio files + shared guestbook API.

GET  /api/messages  -> [{"name","rating","text","date"}, ...] (newest first)
POST /api/messages  {"name","rating":1-5,"text"} -> {"ok":true}
GET  /api/scores    -> top 10 [{"name","score","level"}]
POST /api/scores    {"username","score","level"} -> {"ok":true}
POST /api/claim     {"username","token"} -> {"ok":true,"token"} or {"taken":true}
"""
import json
import os
import secrets
from datetime import date
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.environ.get('SITE_DIR', os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'messages.json')
SCORES = os.path.join(ROOT, 'scores.json')
OWNERS = os.path.join(ROOT, 'owners.json')
RUSH = os.path.join(ROOT, 'rush.json')
CHEERS = os.path.join(ROOT, 'cheers.json')
VISITORS = os.path.join(ROOT, 'visitors.json')
MAX_MSGS = 100
MAX_VISITORS = 200


def load():
    try:
        with open(DB, encoding='utf-8') as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except Exception:
        return []


def load_scores():
    try:
        with open(SCORES, encoding='utf-8') as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def load_owners():
    try:
        with open(OWNERS, encoding='utf-8') as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_owners(d):
    tmp = OWNERS + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, OWNERS)


def clean_name(s):
    return ''.join(ch for ch in str(s)[:20].strip() if ch.isalnum() or ch in ' _-')


def load_json_dict(path):
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_json(path, d):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, path)


def load_visitors():
    try:
        with open(VISITORS, encoding='utf-8') as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except Exception:
        return []


def save_visitors(v):
    tmp = VISITORS + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(v[:MAX_VISITORS], f, ensure_ascii=False)
    os.replace(tmp, VISITORS)


def top_scores(n=10):
    d = load_scores()
    rows = [{'name': k, 'score': v.get('score', 0), 'level': v.get('level', 1)}
            for k, v in d.items()]
    rows.sort(key=lambda r: (-r['score'], -r['level']))
    return rows[:n]


def save(msgs):
    tmp = DB + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(msgs, f, ensure_ascii=False)
    os.replace(tmp, DB)


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/messages':
            body = json.dumps(load(), ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/api/scores':
            body = json.dumps(top_scores(), ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/api/rush':
            d = load_json_dict(RUSH)
            rows = [{'name': k, 'score': v.get('score', 0), 'solved': v.get('solved', 0)}
                    for k, v in d.items()]
            rows.sort(key=lambda r: (-r['score'], -r['solved']))
            body = json.dumps(rows[:10], ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/api/cheers':
            body = json.dumps(load_json_dict(CHEERS), ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/api/visitors':
            body = json.dumps(load_visitors(), ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def _read_json(self):
        try:
            ln = int(self.headers.get('Content-Length') or 0)
        except Exception:
            ln = 0
        try:
            return json.loads(self.rfile.read(min(ln, 10000)).decode('utf-8', 'ignore'))
        except Exception:
            return {}

    def _json_ok(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path == '/api/visit':
            data = self._read_json()
            name = str(data.get('name', ''))[:60].strip()
            fb = str(data.get('fb', ''))[:200].strip()
            email = str(data.get('email', ''))[:100].strip()
            if not name:
                self.send_response(400)
                self._cors()
                self.end_headers()
                return
            if email and ('@' not in email or '.' not in email):
                self.send_response(400)
                self._cors()
                self.end_headers()
                return
            v = load_visitors()
            v.insert(0, {'name': name, 'fb': fb, 'email': email,
                         'date': date.today().isoformat(),
                         'ip': (self.client_address[0] if self.client_address else '')})
            save_visitors(v)
            self._json_ok({'ok': True})
            return
        if self.path == '/api/rush':
            data = self._read_json()
            name = clean_name(data.get('username', ''))
            token = str(data.get('token', ''))[:32]
            owners = load_owners()
            if not name or owners.get(name) != token or not token:
                self._json_ok({'error': 'not-owner'})
                return
            try:
                score = int(data.get('score', 0))
            except Exception:
                score = 0
            try:
                solved = int(data.get('solved', 0))
            except Exception:
                solved = 0
            score = max(0, min(20000, score))
            solved = max(0, min(200, solved))
            d = load_json_dict(RUSH)
            old = d.get(name, {'score': 0, 'solved': 0})
            if score > old.get('score', 0):
                d[name] = {'score': score, 'solved': solved}
                save_json(RUSH, d)
            self._json_ok({'ok': True})
            return
        if self.path == '/api/cheer':
            data = self._read_json()
            try:
                idx = int(data.get('id', -1))
            except Exception:
                idx = -1
            if 0 <= idx < 50:
                d = load_json_dict(CHEERS)
                d[str(idx)] = int(d.get(str(idx), 0)) + 1
                save_json(CHEERS, d)
                self._json_ok({'ok': True, 'count': d[str(idx)]})
            else:
                self._json_ok({'error': 'bad-id'})
            return
        if self.path == '/api/claim':
            data = self._read_json()
            name = clean_name(data.get('username', ''))
            token = str(data.get('token', ''))[:32]
            if not name:
                self._json_ok({'error': 'empty'})
                return
            owners = load_owners()
            if name not in owners:
                token = secrets.token_hex(8)
                owners[name] = token
                save_owners(owners)
                self._json_ok({'ok': True, 'token': token})
            elif owners[name] == token and token:
                self._json_ok({'ok': True, 'token': token})
            else:
                self._json_ok({'taken': True})
            return
        if self.path == '/api/scores':
            data = self._read_json()
            name = clean_name(data.get('username', ''))
            token = str(data.get('token', ''))[:32]
            owners = load_owners()
            if not name or owners.get(name) != token or not token:
                self._json_ok({'error': 'not-owner'})
                return
            try:
                score = int(data.get('score', 0))
            except Exception:
                score = 0
            try:
                level = int(data.get('level', 1))
            except Exception:
                level = 1
            score = max(0, min(20000, score))
            level = max(1, min(10, level))
            d = load_scores()
            old = d.get(name, {'score': 0, 'level': 1})
            if score > old.get('score', 0):
                d[name] = {'score': score, 'level': level}
                tmp = SCORES + '.tmp'
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump(d, f, ensure_ascii=False)
                os.replace(tmp, SCORES)
            self._json_ok({'ok': True})
            return
        if self.path != '/api/messages':
            self.send_response(404)
            self._cors()
            self.end_headers()
            return
        data = self._read_json()
        name = str(data.get('name', 'A visitor'))[:60].strip() or 'A visitor'
        text = str(data.get('text', ''))[:1000].strip()
        try:
            rating = int(data.get('rating', 0))
        except Exception:
            rating = 0
        if rating < 1 or rating > 5 or not text:
            self.send_response(400)
            self._cors()
            self.end_headers()
            return
        msgs = load()
        msgs.insert(0, {'name': name, 'rating': rating, 'text': text,
                        'date': date.today().isoformat()})
        save(msgs[:MAX_MSGS])
        body = b'{"ok":true}'
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8080'))
    ThreadingHTTPServer(('0.0.0.0', port), H).serve_forever()
