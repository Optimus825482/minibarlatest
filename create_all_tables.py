#!/usr/bin/env python3
"""
Create all database tables
"""

from app import app, db
from models import *

with app.app_context():
    try:
        print("\n🔄 Creating all database tables...")
        
        # Create all tables
        db.create_all()
        
        print("✅ All tables created successfully!")
        
        # Verify
        from sqlalchemy import text
        result = db.session.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)).fetchall()
        
        print(f"\n📊 Created {len(result)} tables:")
        for row in result:
            print(f"   ✅ {row[0]}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
