from datetime import datetime, date, timezone
import zoneinfo

def to_ist(dt, fmt=None):
    """
    Convert a UTC datetime to Asia/Kolkata (IST).
    If fmt is provided, returns a formatted string.
    """
    if not dt:
        return dt
        
    if not isinstance(dt, datetime) and isinstance(dt, date):
        if fmt:
            return dt.strftime(fmt)
        return dt
        
    ist = zoneinfo.ZoneInfo('Asia/Kolkata')
    
    if hasattr(dt, 'tzinfo') and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        
    local_dt = dt.astimezone(ist)
    if fmt:
        return local_dt.strftime(fmt)
    return local_dt
