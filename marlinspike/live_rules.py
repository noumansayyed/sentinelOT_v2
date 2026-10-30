import os
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

OFF_HOURS_START = int(os.environ.get("OFF_HOURS_START", "22"))
OFF_HOURS_END   = int(os.environ.get("OFF_HOURS_END", "6"))
PLANT_TZ_NAME   = os.environ.get("PLANT_TIMEZONE", "UTC")
try:
    PLANT_TZ = ZoneInfo(PLANT_TZ_NAME)
except Exception:
    PLANT_TZ = timezone.utc

BYTES_PER_CONV_ALERT = 50 * 1024 * 1024
BEACON_MIN_FILES     = 3
BEACON_MAX_BYTES_CV  = 0.05


def evaluate(conv, asset_state, now=None):
    now = now or datetime.now(timezone.utc)
    alerts = []
    src  = conv.get("src_ip") or ""
    dst  = conv.get("dst_ip") or ""
    proto = conv.get("protocol") or "Unknown"
    if not src:
        return alerts

    if src not in asset_state:
        alerts.append(_alert("NEW_ASSET", "HIGH",
            f"New asset detected: {src} has not been seen before. "
            f"First protocol: {proto}, peer: {dst or 'unknown'}. "
            f"Verify this host is expected on the OT segment.",
            src, dst, proto))

    known = asset_state.get(src, {}).get("protocols", set())
    if proto and proto not in known and known:
        alerts.append(_alert("NEW_PROTOCOL", "HIGH",
            f"New protocol on existing asset: {src} is now speaking {proto}. "
            f"Known: {', '.join(sorted(known))}.",
            src, dst, proto))

    if _is_off_hours(now):
        alerts.append(_alert("OFF_HOURS", "MEDIUM",
            f"Off-hours OT traffic: {src} -> {dst} spoke {proto} outside "
            f"the plant business-hours window ({OFF_HOURS_START:02d}:00-"
            f"{OFF_HOURS_END:02d}:00 {PLANT_TZ_NAME}). Cross-check the "
            f"plant change calendar before acting.",
            src, dst, proto))

    if conv.get("includes_writes"):
        op = conv.get("operation") or "write"
        alerts.append(_alert("WRITE_ANOMALY", "CRITICAL",
            f"Write-class operation observed: {src} -> {dst} over {proto} "
            f"performed a '{op}' operation. Verify whether this source is "
            f"an authorized engineering workstation.",
            src, dst, proto))

    b = float(conv.get("bytes_total") or 0)
    if b >= BYTES_PER_CONV_ALERT:
        alerts.append(_alert("THRESHOLD_ANOMALY", "HIGH",
            f"Threshold exceeded: {src} -> {dst} ({proto}) transferred "
            f"{b / (1024*1024):.1f} MB in one conversation.",
            src, dst, proto))

    bucket = asset_state.get(src, {}).get("byte_buckets", {}).get(proto)
    if bucket and len(bucket) >= BEACON_MIN_FILES:
        vals = list(bucket)
        mean = sum(vals) / len(vals)
        if mean > 0:
            cv = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5 / mean
            if cv < BEACON_MAX_BYTES_CV:
                alerts.append(_alert("UNUSUAL_COMMUNICATION", "HIGH",
                    f"Unusual communication pattern: {src} -> {dst} over "
                    f"{proto} has appeared in {len(bucket)} distinct capture "
                    f"files with near-identical byte counts (CV={cv:.3f}). "
                    f"Steady size-and-cadence traffic on OT is a beacon "
                    f"proxy; verify against expected poll loops.",
                    src, dst, proto))

    return alerts


def _alert(rule, severity, text, src, dst, proto):
    return {"rule": rule, "severity": severity, "text": text,
            "src_ip": src, "dst_ip": dst, "protocol": proto}


def _is_off_hours(now):
    local = now.astimezone(PLANT_TZ)
    h = local.hour
    return h >= OFF_HOURS_START or h < OFF_HOURS_END
