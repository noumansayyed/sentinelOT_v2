from datetime import datetime, timezone

OFF_HOURS_START = 22
OFF_HOURS_END = 6
BYTES_PER_CONV_ALERT = 50 * 1024 * 1024

def evaluate(conv, asset_state, now=None):
    now = now or datetime.now(timezone.utc)
    alerts = []
    src = conv.get("src_ip") or ""
    dst = conv.get("dst_ip") or ""
    proto = conv.get("protocol") or "Unknown"

    # Skip low-layer frames that have no IP (ARP, bare ethernet)
    if not src:
        return alerts

    if src not in asset_state:
        alerts.append(_alert("NEW_ASSET", "HIGH",
            f"New asset detected: {src} has not been seen before in this "
            f"monitoring session. First observed protocol: {proto}, "
            f"peer: {dst or 'unknown'}. Verify this host is expected on "
            f"the OT segment.",
            src, dst, proto))

    known = asset_state.get(src, {}).get("protocols", set())
    if proto and proto not in known and known:
        alerts.append(_alert("NEW_PROTOCOL", "HIGH",
            f"New protocol on existing asset: {src} is now speaking "
            f"{proto}, which it has not used before. Known protocols: "
            f"{', '.join(sorted(known))}.",
            src, dst, proto))

    # OFF_HOURS disabled until PLANT_TIMEZONE is configurable.
    # The rule as written compares UTC container time to a fixed
    # 22:00-06:00 window, which produces false positives on any capture
    # taken outside that UTC window regardless of the plant's actual
    # local time. Re-enable when a per-deployment timezone is wired in.
    # if conv.get("first_seen") and _is_off_hours(now):
    #     alerts.append(_alert("OFF_HOURS", "MEDIUM",
    #         f"Off-hours OT traffic: {src} -> {dst} spoke {proto} "
    #         f"outside business hours. Cross-check with the plant change "
    #         f"calendar before acting.",
    #         src, dst, proto))

    if conv.get("includes_writes"):
        op = conv.get("operation") or "write"
        alerts.append(_alert("WRITE_ANOMALY", "CRITICAL",
            f"Write-class operation observed: {src} -> {dst} over "
            f"{proto} performed a '{op}' operation. Verify whether this "
            f"source is an authorized engineering workstation.",
            src, dst, proto))

    b = float(conv.get("bytes_total") or 0)
    if b >= BYTES_PER_CONV_ALERT:
        alerts.append(_alert("THRESHOLD_ANOMALY", "HIGH",
            f"Threshold exceeded: {src} -> {dst} ({proto}) transferred "
            f"{b / (1024*1024):.1f} MB in a single capture file.",
            src, dst, proto))

    return alerts

def _alert(rule, severity, text, src, dst, proto):
    return {"rule": rule, "severity": severity, "text": text,
            "src_ip": src, "dst_ip": dst, "protocol": proto}

def _is_off_hours(now):
    return now.hour >= OFF_HOURS_START or now.hour < OFF_HOURS_END
