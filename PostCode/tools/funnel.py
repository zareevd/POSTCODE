"""Count distinct demo sessions for each stage among landing visitors."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.server.repositories.store import transaction

steps = ("landing_view","calculator_completed","subscribe_click","waitlist_submitted","payment_success","benefit_used")
with transaction() as conn:
    rows = conn.execute("""SELECT event, count(DISTINCT sid) FROM events
                           WHERE sid IN (SELECT sid FROM events WHERE event='landing_view')
                           GROUP BY event""")
    counts = dict(rows)
for step in steps:
    count = counts.get(step,0)
    visitors = counts.get("landing_view",0)
    print(f"{step:24} {count:5}   {100*count/visitors if visitors else 0:5.1f}%")
