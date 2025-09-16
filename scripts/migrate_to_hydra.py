#!/usr/bin/env python3
"""
Migration script for transitioning from legacy configuration system to Hydra + Pydantic.

This script helps users migrate their existing siege_utilities configurations
to the new Hydra + Pydantic system while maintaining backward compatibility.
"""

import sys
import argparse
from pathlib import Path
import logging

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from siege_utilities.config.migration import migrate_configurations, backup_and_migrate, ConfigurationMigrator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main migration script entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate siege_utilities configurations to Hydra + Pydantic system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be migrated
  python migrate_to_hydra.py --dry-run
  
  # Migrate with backup
  python migrate_to_hydra.py --backup
  
  # Migrate from custom legacy directory
  python migrate_to_hydra.py --legacy-config ~/old_siege_config --backup
  
  # Just create backup without migration
  python migrate_to_hydra.py --backup-only
        """
    )
    
    parser.add_argument(
        "--legacy-config",
        type=Path,
        help="Path to legacy configuration directory (default: ~/.siege_utilities/config)"
    )
    
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="Path to backup directory (default: auto-generated with timestamp)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup before migration"
    )
    
    parser.add_argument(
        "--backup-only",
        action="store_true",
        help="Only create backup, do not migrate"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting siege_utilities configuration migration")
    logger.info(f"Legacy config directory: {args.legacy_config or '~/.siege_utilities/config'}")
    
    try:
        if args.backup_only:
            # Only create backup
            migrator = ConfigurationMigrator(args.legacy_config)
            backup_path = migrator.backup_legacy_configurations(args.backup_dir)
            logger.info(f"✅ Backup created successfully: {backup_path}")
            return 0
        
        if args.backup:
            # Backup and migrate
            logger.info("Creating backup and migrating configurations...")
            results = backup_and_migrate(args.legacy_config, args.backup_dir)
            backup_location = results.get("backup_location", "Unknown")
            logger.info(f"✅ Backup created: {backup_location}")
        else:
            # Just migrate
            logger.info("Migrating configurations...")
            results = migrate_configurations(args.legacy_config, args.dry_run)
        
        # Report results
        if args.dry_run:
            logger.info("🔍 Dry run completed - no changes made")
        else:
            logger.info("✅ Migration completed successfully")
        
        logger.info(f"📊 Migration Summary:")
        logger.info(f"  - User profile: {'✅ Migrated' if results['user_profile']['migrated'] else '❌ Failed'}")
        logger.info(f"  - Client profiles: {len(results['client_profiles']['migrated'])} migrated")
        
        if results['client_profiles']['migrated']:
            logger.info(f"  - Migrated clients: {', '.join(results['client_profiles']['migrated'])}")
        
        if results['client_profiles']['errors']:
            logger.warning(f"  - Errors: {len(results['client_profiles']['errors'])}")
            for error in results['client_profiles']['errors']:
                logger.warning(f"    - {error}")
        
        if 'backup_location' in results:
            logger.info(f"  - Backup location: {results['backup_location']}")
        
        if results.get('error'):
            logger.error(f"❌ Migration failed: {results['error']}")
            return 1
        
        logger.info("🎉 Migration completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Test your configurations with the new system")
        logger.info("2. Update any custom scripts to use the new API")
        logger.info("3. Remove old configuration files once you're satisfied")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Migration failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
