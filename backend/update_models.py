import os
import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
        
    original = content

    # Add UTC to datetime import
    if 'from datetime import datetime' in content and 'UTC' not in content:
        content = content.replace('from datetime import datetime', 'from datetime import datetime, UTC')
    elif 'from datetime import date, datetime' in content and 'UTC' not in content:
        content = content.replace('from datetime import date, datetime', 'from datetime import date, datetime, UTC')
    
    # Add DateTime import if missing
    if 'DateTime' not in content:
        if 'from sqlalchemy import ' in content:
            # find first occurrence
            content = re.sub(r'from sqlalchemy import (.*?)\n', r'from sqlalchemy import \1, DateTime\n', content, count=1)
        else:
            # Add after other sqlalchemy imports
            content = re.sub(r'(from sqlalchemy\..*?\n)', r'\1from sqlalchemy import DateTime\n', content, count=1)
            
    # Replace default=datetime.utcnow
    content = re.sub(r'default\s*=\s*datetime\.utcnow', 'default=lambda: datetime.now(UTC)', content)
    
    # Replace mapped_column(...) with mapped_column(DateTime(timezone=True), ...)
    # where it is a datetime column
    # Pattern: : Mapped[datetime] = mapped_column(
    content = re.sub(r'(:\s*Mapped\[datetime(?: \| None)?\]\s*=\s*mapped_column\()', r'\1DateTime(timezone=True), ', content)
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Updated {filepath}")

app_dir = "backend/app"
for root, dirs, files in os.walk(app_dir):
    for f in files:
        if f == 'models.py':
            process_file(os.path.join(root, f))
