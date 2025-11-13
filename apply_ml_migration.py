#!/usr/bin/env python3
"""
ML Model Path Migration Script
Adds model_path column to ml_models table
"""

from app import app, db
from sqlalchemy import text

def apply_migration():
    """Apply migration: add model_path column"""
    with app.app_context():
        try:
            print("🔄 Applying ML model_path migration...")
            
            # Check if column already exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='ml_models' AND column_name='model_path'
            """)
            
            result = db.session.execute(check_query).fetchone()
            
            if result:
                print("⏭️  model_path column already exists, skipping...")
                return True
            
            # Add model_path column
            print("📝 Adding model_path column...")
            db.session.execute(text("""
                ALTER TABLE ml_models 
                ADD COLUMN model_path VARCHAR(500) NULL
            """))
            
            # Make model_data nullable
            print("📝 Making model_data nullable...")
            db.session.execute(text("""
                ALTER TABLE ml_models 
                ALTER COLUMN model_data DROP NOT NULL
            """))
            
            # Add index
            print("📝 Adding index on model_path...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ml_models_path 
                ON ml_models(model_path)
            """))
            
            db.session.commit()
            
            print("✅ Migration applied successfully!")
            print("   - model_path column added")
            print("   - model_data made nullable")
            print("   - idx_ml_models_path index created")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")
            return False

def rollback_migration():
    """Rollback migration: remove model_path column"""
    with app.app_context():
        try:
            print("🔄 Rolling back ML model_path migration...")
            
            # Drop index
            print("📝 Dropping index...")
            db.session.execute(text("""
                DROP INDEX IF EXISTS idx_ml_models_path
            """))
            
            # Make model_data NOT NULL again
            print("📝 Making model_data NOT NULL...")
            db.session.execute(text("""
                ALTER TABLE ml_models 
                ALTER COLUMN model_data SET NOT NULL
            """))
            
            # Drop model_path column
            print("📝 Dropping model_path column...")
            db.session.execute(text("""
                ALTER TABLE ml_models 
                DROP COLUMN IF EXISTS model_path
            """))
            
            db.session.commit()
            
            print("✅ Migration rolled back successfully!")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Rollback failed: {str(e)}")
            return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        rollback_migration()
    else:
        apply_migration()
