import os
import csv
import io
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# ==================== DATABASE CONFIG ====================
# Use PostgreSQL if DATABASE_URL is set (Render), else SQLite
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Render uses 'postgres://' but SQLAlchemy wants 'postgresql://'
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Local SQLite (fallback)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    os.makedirs(DATA_DIR, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(DATA_DIR, "shows.db").replace(chr(92), "/")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'vfx-tracker-secret-key-2026')
# ========================================================

db = SQLAlchemy(app)

# ==================== MODELS ====================
class Show(db.Model):
    __tablename__ = 'shows'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    client = db.Column(db.String(200))
    producer = db.Column(db.String(200))
    vfx_supervisor = db.Column(db.String(200))
    comp_supervisor = db.Column(db.String(200))
    start_date = db.Column(db.String(50))
    delivery_date = db.Column(db.String(50))
    budget = db.Column(db.String(100))
    fps = db.Column(db.String(20), default='24')
    resolution = db.Column(db.String(50), default='1920x1080')
    colorspace = db.Column(db.String(50), default='ACES')
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='Active')
    created_at = db.Column(db.String(50), default=lambda: datetime.now().isoformat())

class Sequence(db.Model):
    __tablename__ = 'sequences'
    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('shows.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.String(50), default=lambda: datetime.now().isoformat())

class Artist(db.Model):
    __tablename__ = 'artists'
    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('shows.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(100))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    rate = db.Column(db.String(50))
    role = db.Column(db.String(100))
    created_at = db.Column(db.String(50), default=lambda: datetime.now().isoformat())

class Shot(db.Model):
    __tablename__ = 'shots'
    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('shows.id'), nullable=False)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequences.id'))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    shot_type = db.Column(db.String(100))
    frames = db.Column(db.String(50))
    duration = db.Column(db.String(50))
    status = db.Column(db.String(50), default='Not Started')
    priority = db.Column(db.String(50), default='Normal')
    assigned_to = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.String(50), default=lambda: datetime.now().isoformat())
    updated_at = db.Column(db.String(50), default=lambda: datetime.now().isoformat())

class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('shows.id'))
    action = db.Column(db.String(500))
    timestamp = db.Column(db.String(50), default=lambda: datetime.now().isoformat())

# =============================================================================
# CONSTANTS
# =============================================================================

STATUS_COLORS = {
    "Not Started": "#6b7280",
    "WIP": "#fbbf24",
    "Review": "#60a5fa",
    "Approved": "#4ade80",
    "On Hold": "#f87171",
    "Omit": "#888888"
}

STATUS_BG_COLORS = {
    "Not Started": "rgba(107, 114, 128, 0.15)",
    "WIP": "rgba(251, 191, 36, 0.15)",
    "Review": "rgba(96, 165, 250, 0.15)",
    "Approved": "rgba(74, 222, 128, 0.15)",
    "On Hold": "rgba(248, 113, 113, 0.15)",
    "Omit": "rgba(136, 136, 136, 0.15)"
}

SHOT_TYPES = ["VFX", "CG", "Cleanup", "Roto", "Matchmove", "Paint", "Compositing", "Full CG", "Element"]
DEPARTMENTS = ["Compositing", "Lighting", "FX", "Animation", "Roto", "Prep", "Matchmove", "Concept"]
PRIORITIES = ["Low", "Normal", "High", "Critical"]
STATUSES = ["Not Started", "WIP", "Review", "Approved", "On Hold", "Omit"]

# =============================================================================
# HELPERS
# =============================================================================

def log_action(show_id, action):
    h = History(show_id=show_id, action=action)
    db.session.add(h)
    db.session.commit()

def get_show_stats(show_id):
    shots = Shot.query.filter_by(show_id=show_id).all()
    sequences = Sequence.query.filter_by(show_id=show_id).all()
    artists = Artist.query.filter_by(show_id=show_id).all()
    counts = {s: 0 for s in STATUSES}
    for shot in shots:
        if shot.status in counts:
            counts[shot.status] += 1
    return {
        "shot_count": len(shots),
        "seq_count": len(sequences),
        "artist_count": len(artists),
        "status_counts": counts
    }

def parse_shot_pattern(pattern, count):
    """Parse a shot name pattern and generate numbered variants."""
    matches = list(re.finditer(r'(\d+)', pattern))
    if not matches:
        return [pattern] if count == 1 else []
    last_match = matches[-1]
    num_str = last_match.group(1)
    num_len = len(num_str)
    start_num = int(num_str)
    prefix = pattern[:last_match.start()]
    suffix = pattern[last_match.end():]
    result = []
    for i in range(start_num, start_num + count):
        new_num = str(i).zfill(num_len)
        result.append(f"{prefix}{new_num}{suffix}")
    return result

# =============================================================================
# ROUTES - MAIN PAGES
# =============================================================================

@app.route('/')
def index():
    shows = Show.query.all()
    return render_template('index.html', shows=shows)

@app.route('/artist_view')
def artist_view():
    return render_template('artist_view.html')

# =============================================================================
# API - SHOWS
# =============================================================================

@app.route('/api/shows', methods=['GET'])
def get_shows():
    shows = Show.query.all()
    return jsonify([{
        "id": s.id, "name": s.name, "client": s.client, "producer": s.producer,
        "vfx_supervisor": s.vfx_supervisor, "comp_supervisor": s.comp_supervisor,
        "start_date": s.start_date, "delivery_date": s.delivery_date,
        "budget": s.budget, "fps": s.fps, "resolution": s.resolution,
        "colorspace": s.colorspace, "notes": s.notes, "status": s.status,
        "created_at": s.created_at
    } for s in shows])

@app.route('/api/shows', methods=['POST'])
def create_show():
    data = request.json
    show = Show(
        name=data.get('name', ''),
        client=data.get('client', ''),
        producer=data.get('producer', ''),
        vfx_supervisor=data.get('vfx_supervisor', ''),
        comp_supervisor=data.get('comp_supervisor', ''),
        start_date=data.get('start_date', ''),
        delivery_date=data.get('delivery_date', ''),
        budget=data.get('budget', ''),
        fps=data.get('fps', '24'),
        resolution=data.get('resolution', '1920x1080'),
        colorspace=data.get('colorspace', 'ACES'),
        notes=data.get('notes', ''),
        status=data.get('status', 'Active')
    )
    db.session.add(show)
    db.session.commit()
    log_action(show.id, f"Show '{show.name}' created")
    return jsonify({"success": True, "id": show.id})

@app.route('/api/shows/<int:show_id>', methods=['GET'])
def get_show(show_id):
    show = Show.query.get_or_404(show_id)
    return jsonify({
        "id": show.id, "name": show.name, "client": show.client,
        "producer": show.producer, "vfx_supervisor": show.vfx_supervisor,
        "comp_supervisor": show.comp_supervisor, "start_date": show.start_date,
        "delivery_date": show.delivery_date, "budget": show.budget,
        "fps": show.fps, "resolution": show.resolution,
        "colorspace": show.colorspace, "notes": show.notes, "status": show.status
    })

@app.route('/api/shows/<int:show_id>', methods=['PUT'])
def update_show(show_id):
    show = Show.query.get_or_404(show_id)
    data = request.json
    show.name = data.get('name', show.name)
    show.client = data.get('client', show.client)
    show.producer = data.get('producer', show.producer)
    show.vfx_supervisor = data.get('vfx_supervisor', show.vfx_supervisor)
    show.comp_supervisor = data.get('comp_supervisor', show.comp_supervisor)
    show.start_date = data.get('start_date', show.start_date)
    show.delivery_date = data.get('delivery_date', show.delivery_date)
    show.budget = data.get('budget', show.budget)
    show.fps = data.get('fps', show.fps)
    show.resolution = data.get('resolution', show.resolution)
    show.colorspace = data.get('colorspace', show.colorspace)
    show.notes = data.get('notes', show.notes)
    show.status = data.get('status', show.status)
    db.session.commit()
    log_action(show_id, f"Show '{show.name}' updated")
    return jsonify({"success": True})

@app.route('/api/shows/<int:show_id>', methods=['DELETE'])
def delete_show(show_id):
    show = Show.query.get_or_404(show_id)
    name = show.name
    Shot.query.filter_by(show_id=show_id).delete()
    Sequence.query.filter_by(show_id=show_id).delete()
    Artist.query.filter_by(show_id=show_id).delete()
    History.query.filter_by(show_id=show_id).delete()
    db.session.delete(show)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/shows/<int:show_id>/stats', methods=['GET'])
def show_stats(show_id):
    return jsonify(get_show_stats(show_id))

# =============================================================================
# API - SEQUENCES
# =============================================================================

@app.route('/api/shows/<int:show_id>/sequences', methods=['GET'])
def get_sequences(show_id):
    seqs = Sequence.query.filter_by(show_id=show_id).all()
    return jsonify([{"id": s.id, "name": s.name, "description": s.description, "created_at": s.created_at} for s in seqs])

@app.route('/api/shows/<int:show_id>/sequences', methods=['POST'])
def create_sequence(show_id):
    data = request.json
    seq = Sequence(show_id=show_id, name=data.get('name', ''), description=data.get('description', ''))
    db.session.add(seq)
    db.session.commit()
    log_action(show_id, f"Sequence '{seq.name}' added")
    return jsonify({"success": True, "id": seq.id})

@app.route('/api/sequences/<int:seq_id>', methods=['PUT'])
def update_sequence(seq_id):
    seq = Sequence.query.get_or_404(seq_id)
    data = request.json
    seq.name = data.get('name', seq.name)
    seq.description = data.get('description', seq.description)
    db.session.commit()
    log_action(seq.show_id, f"Sequence '{seq.name}' updated")
    return jsonify({"success": True})

@app.route('/api/sequences/<int:seq_id>', methods=['DELETE'])
def delete_sequence(seq_id):
    seq = Sequence.query.get_or_404(seq_id)
    show_id = seq.show_id
    name = seq.name
    Shot.query.filter_by(sequence_id=seq_id).update({"sequence_id": None})
    db.session.delete(seq)
    db.session.commit()
    log_action(show_id, f"Sequence '{name}' deleted")
    return jsonify({"success": True})

# =============================================================================
# API - ARTISTS
# =============================================================================

@app.route('/api/shows/<int:show_id>/artists', methods=['GET'])
def get_artists(show_id):
    artists = Artist.query.filter_by(show_id=show_id).all()
    return jsonify([{
        "id": a.id, "name": a.name, "department": a.department,
        "email": a.email, "phone": a.phone, "rate": a.rate, "role": a.role
    } for a in artists])

@app.route('/api/shows/<int:show_id>/artists', methods=['POST'])
def create_artist(show_id):
    data = request.json
    artist = Artist(
        show_id=show_id, name=data.get('name', ''), department=data.get('department', ''),
        email=data.get('email', ''), phone=data.get('phone', ''),
        rate=data.get('rate', ''), role=data.get('role', '')
    )
    db.session.add(artist)
    db.session.commit()
    log_action(show_id, f"Artist '{artist.name}' added")
    return jsonify({"success": True, "id": artist.id})

@app.route('/api/artists/<int:artist_id>', methods=['PUT'])
def update_artist(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    data = request.json
    artist.name = data.get('name', artist.name)
    artist.department = data.get('department', artist.department)
    artist.email = data.get('email', artist.email)
    artist.phone = data.get('phone', artist.phone)
    artist.rate = data.get('rate', artist.rate)
    artist.role = data.get('role', artist.role)
    db.session.commit()
    log_action(artist.show_id, f"Artist '{artist.name}' updated")
    return jsonify({"success": True})

@app.route('/api/artists/<int:artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    show_id = artist.show_id
    name = artist.name
    Shot.query.filter_by(assigned_to=name, show_id=show_id).update({"assigned_to": None})
    db.session.delete(artist)
    db.session.commit()
    log_action(show_id, f"Artist '{name}' deleted")
    return jsonify({"success": True})

# =============================================================================
# API - SHOTS
# =============================================================================

@app.route('/api/shows/<int:show_id>/shots', methods=['GET'])
def get_shots(show_id):
    shots = Shot.query.filter_by(show_id=show_id).all()
    return jsonify([{
        "id": s.id, "sequence_id": s.sequence_id, "name": s.name,
        "description": s.description, "shot_type": s.shot_type,
        "frames": s.frames, "duration": s.duration, "status": s.status,
        "priority": s.priority, "assigned_to": s.assigned_to, "notes": s.notes,
        "created_at": s.created_at, "updated_at": s.updated_at
    } for s in shots])

@app.route('/api/shows/<int:show_id>/shots', methods=['POST'])
def create_shot(show_id):
    data = request.json
    shot = Shot(
        show_id=show_id, sequence_id=data.get('sequence_id'),
        name=data.get('name', ''), description=data.get('description', ''),
        shot_type=data.get('shot_type', ''), frames=data.get('frames', ''),
        duration=data.get('duration', ''), status=data.get('status', 'Not Started'),
        priority=data.get('priority', 'Normal'), assigned_to=data.get('assigned_to', ''),
        notes=data.get('notes', '')
    )
    db.session.add(shot)
    db.session.commit()
    log_action(show_id, f"Shot '{shot.name}' added")
    return jsonify({"success": True, "id": shot.id})

@app.route('/api/shows/<int:show_id>/shots/bulk', methods=['POST'])
def create_shots_bulk(show_id):
    data = request.json
    pattern = data.get('pattern', '')
    count = int(data.get('count', 0))
    sequence_id = data.get('sequence_id')
    shot_type = data.get('shot_type', '')
    status = data.get('status', 'Not Started')
    priority = data.get('priority', 'Normal')
    assigned_to = data.get('assigned_to', '')
    frames = data.get('frames', '')
    duration = data.get('duration', '')
    notes = data.get('notes', '')
    
    names = parse_shot_pattern(pattern, count)
    created = []
    for name in names:
        shot = Shot(
            show_id=show_id, sequence_id=sequence_id, name=name,
            shot_type=shot_type, status=status, priority=priority,
            assigned_to=assigned_to, frames=frames, duration=duration, notes=notes
        )
        db.session.add(shot)
        created.append(name)
    db.session.commit()
    log_action(show_id, f"Bulk created {len(created)} shots from pattern '{pattern}'")
    return jsonify({"success": True, "created": len(created), "names": names})

@app.route('/api/shots/<int:shot_id>', methods=['PUT'])
def update_shot(shot_id):
    shot = Shot.query.get_or_404(shot_id)
    data = request.json
    shot.sequence_id = data.get('sequence_id', shot.sequence_id)
    shot.name = data.get('name', shot.name)
    shot.description = data.get('description', shot.description)
    shot.shot_type = data.get('shot_type', shot.shot_type)
    shot.frames = data.get('frames', shot.frames)
    shot.duration = data.get('duration', shot.duration)
    shot.status = data.get('status', shot.status)
    shot.priority = data.get('priority', shot.priority)
    shot.assigned_to = data.get('assigned_to', shot.assigned_to)
    shot.notes = data.get('notes', shot.notes)
    shot.updated_at = datetime.now().isoformat()
    db.session.commit()
    log_action(shot.show_id, f"Shot '{shot.name}' updated")
    return jsonify({"success": True})

@app.route('/api/shots/<int:shot_id>', methods=['DELETE'])
def delete_shot(shot_id):
    shot = Shot.query.get_or_404(shot_id)
    show_id = shot.show_id
    name = shot.name
    db.session.delete(shot)
    db.session.commit()
    log_action(show_id, f"Shot '{name}' deleted")
    return jsonify({"success": True})

@app.route('/api/shots/<int:shot_id>/status', methods=['PATCH'])
def update_shot_status(shot_id):
    shot = Shot.query.get_or_404(shot_id)
    data = request.json
    shot.status = data.get('status', shot.status)
    shot.updated_at = datetime.now().isoformat()
    db.session.commit()
    return jsonify({"success": True})

# =============================================================================
# API - ARTIST VIEW (cross-show)
# =============================================================================

@app.route('/api/artist/<name>/shots', methods=['GET'])
def get_artist_shots(name):
    shots = Shot.query.filter_by(assigned_to=name).all()
    result = []
    for shot in shots:
        show = Show.query.get(shot.show_id)
        seq = Sequence.query.get(shot.sequence_id) if shot.sequence_id else None
        result.append({
            "id": shot.id, "name": shot.name, "show_name": show.name if show else "",
            "sequence_name": seq.name if seq else "", "status": shot.status,
            "priority": shot.priority, "shot_type": shot.shot_type,
            "frames": shot.frames, "duration": shot.duration, "notes": shot.notes
        })
    return jsonify(result)

@app.route('/api/artists/all', methods=['GET'])
def get_all_artists():
    artists = Artist.query.all()
    return jsonify([{"name": a.name, "department": a.department} for a in artists])

# =============================================================================
# API - HISTORY
# =============================================================================

@app.route('/api/shows/<int:show_id>/history', methods=['GET'])
def get_history(show_id):
    history = History.query.filter_by(show_id=show_id).order_by(History.id.desc()).limit(100).all()
    return jsonify([{"action": h.action, "timestamp": h.timestamp} for h in history])

# =============================================================================
# API - EXPORT
# =============================================================================

@app.route('/api/shows/<int:show_id>/export/shots', methods=['GET'])
def export_shots(show_id):
    show = Show.query.get_or_404(show_id)
    shots = Shot.query.filter_by(show_id=show_id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Shot Name", "Sequence", "Type", "Frames", "Duration", "Status", "Priority", "Assigned To", "Notes"])
    for shot in shots:
        seq = Sequence.query.get(shot.sequence_id) if shot.sequence_id else None
        writer.writerow([
            shot.name, seq.name if seq else "", shot.shot_type, shot.frames,
            shot.duration, shot.status, shot.priority, shot.assigned_to or "", shot.notes or ""
        ])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"{show.name}_shots.csv"
    )

@app.route('/api/shows/<int:show_id>/export/artists', methods=['GET'])
def export_artists(show_id):
    show = Show.query.get_or_404(show_id)
    artists = Artist.query.filter_by(show_id=show_id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Department", "Email", "Phone", "Rate", "Role"])
    for a in artists:
        writer.writerow([a.name, a.department, a.email or "", a.phone or "", a.rate or "", a.role or ""])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"{show.name}_artists.csv"
    )

# =============================================================================
# INIT
# =============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # No browser auto-open for production
    app.run(host='0.0.0.0', port=5000, debug=False)