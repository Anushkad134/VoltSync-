from datetime import datetime, timedelta, timezone

def generate_timeline(context):
    """Generates the shared timeline for the time-series datasets."""
    # Anchor to 2 days before today at midnight UTC to cover current days
    now = datetime.now(timezone.utc)
    anchor = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc) - timedelta(days=2)
    
    total_minutes = max(context.days, 7) * 24 * 60
    intervals = total_minutes // context.interval
    
    timeline = []
    current = anchor
    for _ in range(intervals):
        timeline.append(current)
        current += timedelta(minutes=context.interval)
        
    return timeline
