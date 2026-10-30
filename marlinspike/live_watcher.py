import glob, json, logging, os, re, subprocess, threading, time
from datetime import datetime, timezone
from marlinspike.models import db
from marlinspike.live_models import LiveAsset, LiveAlert, LiveProcessedFile
from marlinspike.live_rules import evaluate
from marlinspike.live_explainer import explain

log = logging.getLogger(__name__)
CAPTURE_DIR = "/var/lib/marlinspike/captures"
DPI_BIN = "/usr/local/bin/marlinspike-dpi"
SCAN_INTERVAL = 15
PROCESS_GRACE = 5
_watcher_started = False
_lock = threading.Lock()
_asset_cache = {}

def start_watcher(app):
    global _watcher_started
    with _lock:
        if _watcher_started: return
        _watcher_started = True
    t = threading.Thread(target=_loop, args=(app,), daemon=True, name="live-watcher")
    t.start()
    log.info("live_watcher: started, watching %s", CAPTURE_DIR)

def _loop(app):
    with app.app_context(): _seed_asset_cache()
    while True:
        try: _tick(app)
        except Exception: log.exception("live_watcher: tick failed")
        time.sleep(SCAN_INTERVAL)

def _tick(app):
    if not os.path.isdir(CAPTURE_DIR): return
    for path in sorted(glob.glob(os.path.join(CAPTURE_DIR, "*", "*.pcapng")) + glob.glob(os.path.join(CAPTURE_DIR, "*.pcapng"))):
        _process_file(app, path)

def _process_file(app, path):
    try:
        age = time.time() - os.path.getmtime(path)
    except OSError: return
    if age < PROCESS_GRACE: return
    name = os.path.basename(path)
    with app.app_context():
        if LiveProcessedFile.query.filter_by(filename=name).first(): return
        try: events = _run_dpi(path)
        except Exception:
            log.exception("live_watcher: dpi failed on %s", name)
            return
        created = []
        seen = set()
        for conv in events.get("conversations", []):
            for a in evaluate(conv, _asset_cache):
                key = (a["rule"], a["src_ip"], a["dst_ip"], a["protocol"])
                if key in seen:
                    continue
                seen.add(key)
                a["explanation"] = explain(a)
                row = LiveAlert(ts=datetime.now(timezone.utc).isoformat(), rule=a["rule"], severity=a["severity"], src_ip=a["src_ip"], dst_ip=a["dst_ip"], protocol=a["protocol"], message=a["explanation"])
                db.session.add(row)
                created.append(row)
            _update_assets(conv)
        db.session.add(LiveProcessedFile(filename=name, ts=datetime.now(timezone.utc).isoformat()))
        db.session.commit()
        if created: log.info("live_watcher: %s produced %d alert(s)", name, len(created))

def _run_dpi(path):
    if not os.path.isfile(DPI_BIN):
        raise FileNotFoundError(DPI_BIN)
    out = subprocess.run(
        [DPI_BIN, "--input", path, "--format", "bronze"],
        capture_output=True, text=True, timeout=120,
    )
    if out.returncode != 0:
        raise RuntimeError(f"dpi exit {out.returncode}: {out.stderr[:200]}")
    envelope = json.loads(out.stdout or "{}")
    events = []
    for ev in (envelope.get("output") or {}).get("events") or []:
        env = ev.get("envelope") or {}
        fam = ev.get("family") or {}
        proto_tx = fam.get("protocol_transaction") or {}
        ops = proto_tx.get("operation") or ""
        # Word-boundary match: token must be a whole word or followed by a
        # non-letter boundary, so "setup_communication" does NOT match "set",
        # but "set_register" and "write_single_register" DO match.
        _op_l = ops.lower()
        is_write = any(re.search(r"(?:^|[^a-z0-9])" + w + r"(?![a-z])", _op_l) for w in ("write", "program", "download", "force", "set"))
        events.append({
            "src_ip": env.get("src_ip"),
            "dst_ip": env.get("dst_ip"),
            "protocol": env.get("protocol"),
            "bytes_total": env.get("bytes_count") or 0,
            "packet_count": env.get("packet_count") or 0,
            "first_seen": env.get("timestamp"),
            "includes_writes": is_write,
            "operation": ops,
            "family_kind": next(iter(fam.keys()), None),
        })
    return {"conversations": events}

def _seed_asset_cache():
    for asset in LiveAsset.query.all():
        _asset_cache[asset.ip] = {"protocols": set((asset.protocols or "").split(",")) - {""}, "role": asset.role, "first_seen": asset.first_seen}

def _update_assets(conv):
    src = conv.get("src_ip") or conv.get("src_mac")
    if not src: return
    proto = conv.get("protocol"); role = conv.get("role"); now_iso = datetime.now(timezone.utc).isoformat()
    entry = _asset_cache.get(src)
    if entry is None:
        entry = {"protocols": set(), "role": role, "first_seen": now_iso, "byte_buckets": {}}
        _asset_cache[src] = entry
        db.session.add(LiveAsset(ip=src, protocols="", role=role, first_seen=now_iso, last_seen=now_iso))
    if proto: entry["protocols"].add(proto)
    if role and not entry.get("role"): entry["role"] = role
    if proto:
        buckets = entry.setdefault("byte_buckets", {}).setdefault(proto, [])
        b = float(conv.get("bytes_total") or 0)
        buckets.append(b)
        if len(buckets) > 20:
            del buckets[:len(buckets) - 20]
    row = LiveAsset.query.filter_by(ip=src).first()
    if row:
        row.protocols = ",".join(sorted(entry["protocols"]))
        row.role = entry.get("role")
        row.last_seen = now_iso
