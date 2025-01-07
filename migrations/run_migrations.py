import os
import importlib.util
import sqlite3

def get_migration_files():
    """Get all migration files sorted by number."""
    migration_files = []
    for file in os.listdir('migrations'):
        if file.endswith('.py') and file.startswith('0'):
            migration_files.append(file)
    return sorted(migration_files)

def run_migrations(direction='up'):
    """Run all migrations in order."""
    migration_files = get_migration_files()
    
    for file in migration_files:
        print(f"\nRunning migration: {file}")
        
        # Import migration file
        spec = importlib.util.spec_from_file_location(
            file[:-3], 
            os.path.join('migrations', file)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Run migration
        migration = module.Migration()
        try:
            if direction == 'up':
                migration.up()
            else:
                migration.down()
        except Exception as e:
            print(f"Failed to run migration {file}: {e}")
            break

if __name__ == "__main__":
    import sys
    direction = sys.argv[1] if len(sys.argv) > 1 else 'up'
    run_migrations(direction) 