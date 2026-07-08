from datetime import datetime, timezone
import zoneinfo

def to_ist(dt, fmt=None):
    """
    Convert a UTC datetime to Asia/Kolkata (IST).
    If fmt is provided, returns a formatted string.
    """
    if not dt:
        return dt
        
    ist = zoneinfo.ZoneInfo('Asia/Kolkata')
    
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        
    local_dt = dt.astimezone(ist)
    if fmt:
        return local_dt.strftime(fmt)
    return local_dt
