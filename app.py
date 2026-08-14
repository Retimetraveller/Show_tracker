import os
import csv
import io
import re
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# ==================== DATABASE CONFIG ====================
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
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
    thumbnail = db.Column(db.String(500))

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
    client_status = db.Column(db.String(50), default='Not Sent')
    client_notes = db.Column(db.Text)
    client_sent_date = db.Column(db.String(50))
    client_approved_date = db.Column(db.String(50))
    department = db.Column(db.String(200))
    thumbnail = db.Column(db.String(500))
    tasks = db.Column(db.String(500))

class Playlist(db.Model):
    __tablename__ = 'playlists'
    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('shows.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    shot_ids = db.Column(db.Text)  # JSON array
    created_at = db.Column(db.String(50), default=lambda: datetime.now().isoformat())

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

CLIENT_STATUS_COLORS = {
    "Not Sent": "#6b7280",
    "Pending": "#fbbf24",
    "Approved": "#4ade80",
    "Changes Requested": "#f87171",
    "Retake": "#fb923c"
}

SHOT_TYPES = ["VFX", "CG", "Cleanup", "Roto", "Matchmove", "Paint", "Compositing", "Full CG", "Element"]
DEPARTMENTS = ["Animation", "Modeling", "Layout", "Matchmove", "Roto", "Paint", "CFX", "Groom", "RotoAnim", "Lighting", "Compositing", "FX"]
PRIORITIES = ["Low", "Normal", "High", "Critical"]
STATUSES = ["Not Started", "WIP", "Review", "Approved", "On Hold", "Omit"]
CLIENT_STATUSES = ["Not Sent", "Pending", "Approved", "Changes Requested", "Retake"]

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
    client_counts = {s: 0 for s in CLIENT_STATUSES}
    for shot in shots:
        if shot.status in counts:
            counts[shot.status] += 1
        if shot.client_status in client_counts:
            client_counts[shot.client_status] += 1
    return {
        "shot_count": len(shots),
        "seq_count": len(sequences),
        "artist_count": len(artists),
        "status_counts": counts,
        "client_counts": client_counts
    }

def parse_shot_pattern(pattern, count):
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

def get_client_visible_shots(show_id):
    shots = Shot.query.filter_by(show_id=show_id).all()
    return [s for s in shots if s.client_status in ['Approved', 'Changes Requested']]

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

@app.route('/client_updates')
def client_updates():
    return render_template('client_updates.html')

@app.route('/department/<dept_name>')
def department_view(dept_name):
    return render_template('department_view.html', department=dept_name)

@app.route('/playlists')
def playlists():
    return render_template('playlists.html')

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
        "created_at": s.created_at, "thumbnail": s.thumbnail
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
        status=data.get('status', 'Active'),
        thumbnail=data.get('thumbnail', '')
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
        "colorspace": show.colorspace, "notes": show.notes, "status": show.status,
        "thumbnail": show.thumbnail
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
    show.thumbnail = data.get('thumbnail', show.thumbnail)
    db.session.commit()
    log_action(show_id, f"Show '{show.name}' updated")
    return jsonify({"success": True})

@app.route('/api/shows/<int:show_id>', methods=['DELETE'])
def delete_show(show_id):
    data = request.json
    password = data.get('password', '')
    if password != os.environ.get('DELETION_PASSWORD', 'default-password-change-me'):
        return jsonify({"success": False, "error": "Incorrect password"}), 403
    show = Show.query.get_or_404(show_id)
    name = show.name
    Shot.query.filter_by(show_id=show_id).delete()
    Sequence.query.filter_by(show_id=show_id).delete()
    Artist.query.filter_by(show_id=show_id).delete()
    History.query.filter_by(show_id=show_id).delete()
    Playlist.query.filter_by(show_id=show_id).delete()
    db.session.delete(show)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/shows/<int:show_id>/stats', methods=['GET'])
def show_stats(show_id):
    return jsonify(get_show_stats(show_id))

@app.route('/api/shows/<int:show_id>/client_shots', methods=['GET'])
def get_client_shots(show_id):
    shots = get_client_visible_shots(show_id)
    return jsonify([{
        "id": s.id, "sequence_id": s.sequence_id, "name": s.name,
        "shot_type": s.shot_type, "status": s.status, "priority": s.priority,
        "assigned_to": s.assigned_to, "client_status": s.client_status,
        "client_notes": s.client_notes, "client_sent_date": s.client_sent_date,
        "client_approved_date": s.client_approved_date, "department": s.department
    } for s in shots])

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
    data = request.json
    password = data.get('password', '')
    if password != os.environ.get('DELETION_PASSWORD', 'default-password-change-me'):
        return jsonify({"success": False, "error": "Incorrect password"}), 403
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
    data = request.json
    password = data.get('password', '')
    if password != os.environ.get('DELETION_PASSWORD', 'default-password-change-me'):
        return jsonify({"success": False, "error": "Incorrect password"}), 403
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
        "created_at": s.created_at, "updated_at": s.updated_at,
        "client_status": s.client_status, "client_notes": s.client_notes,
        "client_sent_date": s.client_sent_date, "client_approved_date": s.client_approved_date,
        "department": s.department, "thumbnail": s.thumbnail, "tasks": s.tasks
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
        notes=data.get('notes', ''), department=data.get('department', ''),
        client_status=data.get('client_status', 'Not Sent'),
        tasks=data.get('tasks', '')
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
    department = data.get('department', '')
    
    names = parse_shot_pattern(pattern, count)
    created = []
    for name in names:
        shot = Shot(
            show_id=show_id, sequence_id=sequence_id, name=name,
            shot_type=shot_type, status=status, priority=priority,
            assigned_to=assigned_to, frames=frames, duration=duration,
            notes=notes, department=department, client_status='Not Sent'
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
    shot.department = data.get('department', shot.department)
    shot.client_status = data.get('client_status', shot.client_status)
    shot.client_notes = data.get('client_notes', shot.client_notes)
    shot.tasks = data.get('tasks', shot.tasks)
    shot.thumbnail = data.get('thumbnail', shot.thumbnail)
    
    if shot.client_status == 'Pending' and not shot.client_sent_date:
        shot.client_sent_date = datetime.now().isoformat()
    elif shot.client_status == 'Approved' and not shot.client_approved_date:
        shot.client_approved_date = datetime.now().isoformat()
    
    shot.updated_at = datetime.now().isoformat()
    db.session.commit()
    log_action(shot.show_id, f"Shot '{shot.name}' updated")
    return jsonify({"success": True})

@app.route('/api/shots/<int:shot_id>', methods=['DELETE'])
def delete_shot(shot_id):
    data = request.json
    password = data.get('password', '')
    if password != os.environ.get('DELETION_PASSWORD', 'default-password-change-me'):
        return jsonify({"success": False, "error": "Incorrect password"}), 403
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

@app.route('/api/shots/<int:shot_id>/client_status', methods=['PATCH'])
def update_client_status(shot_id):
    shot = Shot.query.get_or_404(shot_id)
    data = request.json
    shot.client_status = data.get('client_status', shot.client_status)
    shot.client_notes = data.get('client_notes', shot.client_notes)
    
    if shot.client_status == 'Pending' and not shot.client_sent_date:
        shot.client_sent_date = datetime.now().isoformat()
    elif shot.client_status == 'Approved' and not shot.client_approved_date:
        shot.client_approved_date = datetime.now().isoformat()
    
    shot.updated_at = datetime.now().isoformat()
    db.session.commit()
    log_action(shot.show_id, f"Shot '{shot.name}' client status updated to {shot.client_status}")
    return jsonify({"success": True})

@app.route('/api/shots/<int:shot_id>/thumbnail', methods=['PATCH'])
def update_shot_thumbnail(shot_id):
    shot = Shot.query.get_or_404(shot_id)
    data = request.json
    shot.thumbnail = data.get('thumbnail', shot.thumbnail)
    db.session.commit()
    return jsonify({"success": True})

# =============================================================================
# API - DEPARTMENT VIEW
# =============================================================================

@app.route('/api/department/<dept_name>/shots')
def get_department_shots(dept_name):
    show_id = request.args.get('show_id', type=int)
    if not show_id:
        return jsonify({"error": "show_id required"}), 400
    
    shots = Shot.query.filter_by(show_id=show_id).all()
    filtered = [s for s in shots if dept_name in (s.department or '').split(',')]
    
    return jsonify([{
        "id": s.id, "sequence_id": s.sequence_id, "name": s.name,
        "description": s.description, "shot_type": s.shot_type,
        "frames": s.frames, "duration": s.duration, "status": s.status,
        "priority": s.priority, "assigned_to": s.assigned_to, "notes": s.notes,
        "client_status": s.client_status, "department": s.department,
        "thumbnail": s.thumbnail
    } for s in filtered])

# =============================================================================
# API - PLAYLISTS
# =============================================================================

@app.route('/api/shows/<int:show_id>/playlists', methods=['GET'])
def get_playlists(show_id):
    playlists = Playlist.query.filter_by(show_id=show_id).all()
    return jsonify([{
        "id": p.id, "name": p.name, "description": p.description,
        "shot_ids": json.loads(p.shot_ids) if p.shot_ids else [],
        "created_at": p.created_at
    } for p in playlists])

@app.route('/api/shows/<int:show_id>/playlists', methods=['POST'])
def create_playlist(show_id):
    data = request.json
    playlist = Playlist(
        show_id=show_id,
        name=data.get('name', ''),
        description=data.get('description', ''),
        shot_ids=json.dumps(data.get('shot_ids', []))
    )
    db.session.add(playlist)
    db.session.commit()
    log_action(show_id, f"Playlist '{playlist.name}' created")
    return jsonify({"success": True, "id": playlist.id})

@app.route('/api/playlists/<int:playlist_id>', methods=['PUT'])
def update_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    data = request.json
    playlist.name = data.get('name', playlist.name)
    playlist.description = data.get('description', playlist.description)
    playlist.shot_ids = json.dumps(data.get('shot_ids', []))
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/playlists/<int:playlist_id>', methods=['DELETE'])
def delete_playlist(playlist_id):
    data = request.json
    password = data.get('password', '')
    if password != os.environ.get('DELETION_PASSWORD', 'default-password-change-me'):
        return jsonify({"success": False, "error": "Incorrect password"}), 403
    playlist = Playlist.query.get_or_404(playlist_id)
    db.session.delete(playlist)
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
            "frames": shot.frames, "duration": shot.duration, "notes": shot.notes,
            "client_status": shot.client_status, "department": shot.department,
            "thumbnail": shot.thumbnail
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
    writer.writerow(["Shot Name", "Sequence", "Type", "Frames", "Duration", "Status", "Priority", "Assigned To", "Client Status", "Department", "Notes"])
    for shot in shots:
        seq = Sequence.query.get(shot.sequence_id) if shot.sequence_id else None
        writer.writerow([
            shot.name, seq.name if seq else "", shot.shot_type, shot.frames,
            shot.duration, shot.status, shot.priority, shot.assigned_to or "",
            shot.client_status, shot.department or "", shot.notes or ""
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
    @app.route('/debug/shots/<int:show_id>')

# =============================================================================
# INIT - CREATE TABLES ON STARTUP
# =============================================================================

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)