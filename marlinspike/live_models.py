from datetime import datetime
from marlinspike.models import db

class LiveAsset(db.Model):
    __tablename__ = "live_assets"
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(64), unique=True, index=True, nullable=False)
    protocols = db.Column(db.Text, default="")
    role = db.Column(db.String(64))
    first_seen = db.Column(db.String(40))
    last_seen = db.Column(db.String(40))

class LiveAlert(db.Model):
    __tablename__ = "live_alerts"
    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.String(40), index=True)
    rule = db.Column(db.String(40), index=True)
    severity = db.Column(db.String(20), index=True)
    src_ip = db.Column(db.String(64), index=True)
    dst_ip = db.Column(db.String(64))
    protocol = db.Column(db.String(40))
    message = db.Column(db.Text)

class LiveProcessedFile(db.Model):
    __tablename__ = "live_processed_files"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, index=True)
    ts = db.Column(db.String(40))
