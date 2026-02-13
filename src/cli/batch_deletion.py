"""
Batch deletion CLI (T072)

Manual testing tool for batch deletion.

Usage:
  python -m src.cli.batch_deletion --dry-run
  python -m src.cli.batch_deletion --force
  python -m src.cli.batch_deletion --help
"""
import logging
import argparse
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import config
from src.lib.database import Base
from src.services.batch_deletion import BatchDeletionService

logger = logging.getLogger(__name__)


def setup_logging():
    """Setup logging for CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def get_db_session():
    """Create database session."""
    engine = create_engine(config.DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Batch deletion CLI for expired groups'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Scan only, do not delete'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force deletion without confirmation'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting batch deletion CLI")
    
    # Get database session
    db = get_db_session()
    
    try:
        # Scan for expired groups
        expired_groups = BatchDeletionService.scan_expired_groups(db)
        
        if not expired_groups:
            logger.info("No expired groups found")
            return 0
        
        logger.info(f"Found {len(expired_groups)} expired groups:")
        for group in expired_groups:
            logger.info(f"  - {group.id}: {group.group_name} (expires: {group.expires_at})")
        
        # Check dry-run mode
        if args.dry_run:
            logger.info("DRY RUN mode: no deletions performed")
            return 0
        
        # Request confirmation unless forced
        if not args.force:
            response = input(f"\nDelete {len(expired_groups)} groups? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Cancellation: no groups deleted")
                return 0
        
        # Run batch deletion
        logger.info("Running batch deletion...")
        stats = BatchDeletionService.run_batch_deletion(db)
        
        # Report results
        logger.info("Batch deletion complete:")
        logger.info(f"  Scanned: {stats['scanned']}")
        logger.info(f"  Deleted: {stats['deleted']}")
        logger.info(f"  Failed: {stats['failed']}")
        logger.info(f"  Retried: {stats['retried']}")
        logger.info(f"  Alerted: {stats['alerted']}")
        
        return 0
    
    except Exception as e:
        logger.exception("Error during batch deletion")
        return 1
    
    finally:
        db.close()


if __name__ == "__main__":
    exit(main())
