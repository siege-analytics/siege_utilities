#!/usr/bin/env python3
"""
Automated Wiki Update System
Keeps the GitHub Wiki synchronized with local wiki directory
"""

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional
import argparse
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WikiUpdater:
    """Automated system to keep GitHub Wiki synchronized with local documentation"""
    
    def __init__(self, wiki_dir: str = "siege_utilities.wiki", 
                 source_dir: str = "wiki"):
        self.wiki_dir = Path(wiki_dir)
        self.source_dir = Path(source_dir)
        self.config_file = Path("wiki_sync_config.json")
        self.sync_log = Path("wiki_sync_log.json")
        
    def load_config(self) -> Dict:
        """Load synchronization configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            "last_sync": None,
            "sync_interval_hours": 24,
            "auto_commit": True,
            "auto_push": False,
            "backup_enabled": True,
            "excluded_files": [".git", ".gitignore", "*.tmp"],
            "included_directories": ["Recipes", "Architecture", "Examples"]
        }
    
    def save_config(self, config: Dict):
        """Save synchronization configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def load_sync_log(self) -> List[Dict]:
        """Load synchronization log"""
        if self.sync_log.exists():
            with open(self.sync_log, 'r') as f:
                return json.load(f)
        return []
    
    def save_sync_log(self, log_entries: List[Dict]):
        """Save synchronization log"""
        with open(self.sync_log, 'w') as f:
            json.dump(log_entries, log_entries, indent=2)
    
    def check_wiki_repo(self) -> bool:
        """Check if wiki repository exists and is accessible"""
        if not self.wiki_dir.exists():
            logger.info(f"Wiki directory {self.wiki_dir} does not exist")
            return False
        
        git_dir = self.wiki_dir / ".git"
        if not git_dir.exists():
            logger.error(f"Wiki directory {self.wiki_dir} is not a git repository")
            return False
        
        return True
    
    def clone_wiki_repo(self) -> bool:
        """Clone the wiki repository"""
        try:
            if self.wiki_dir.exists():
                shutil.rmtree(self.wiki_dir)
            
            logger.info("Cloning wiki repository...")
            result = subprocess.run([
                "git", "clone", 
                "https://github.com/siege-analytics/siege_utilities.wiki.git",
                str(self.wiki_dir)
            ], capture_output=True, text=True, check=True)
            
            logger.info("Wiki repository cloned successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone wiki repository: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error cloning wiki: {e}")
            return False
    
    def backup_wiki(self) -> bool:
        """Create backup of current wiki"""
        if not self.wiki_dir.exists():
            return False
        
        backup_dir = Path(f"wiki_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        try:
            shutil.copytree(self.wiki_dir, backup_dir, ignore=shutil.ignore_patterns('.git'))
            logger.info(f"Wiki backed up to {backup_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup wiki: {e}")
            return False
    
    def sync_files(self) -> Dict[str, int]:
        """Synchronize files from source to wiki directory"""
        stats = {"copied": 0, "updated": 0, "errors": 0}
        
        if not self.source_dir.exists():
            logger.error(f"Source directory {self.source_dir} does not exist")
            stats["errors"] += 1
            return stats
        
        # Get configuration
        config = self.load_config()
        included_dirs = config.get("included_directories", ["Recipes", "Architecture", "Examples"])
        excluded_patterns = config.get("excluded_files", [".git", ".gitignore", "*.tmp"])
        
        for source_subdir in included_dirs:
            source_path = self.source_dir / source_subdir
            wiki_path = self.wiki_dir / source_subdir
            
            if not source_path.exists():
                logger.warning(f"Source subdirectory {source_subdir} does not exist")
                continue
            
            # Create wiki subdirectory if it doesn't exist
            wiki_path.mkdir(exist_ok=True)
            
            # Copy files
            for item in source_path.rglob("*"):
                if item.is_file():
                    # Check if file should be excluded
                    if any(pattern in str(item) for pattern in excluded_patterns):
                        continue
                    
                    # Calculate relative path
                    rel_path = item.relative_to(source_path)
                    target_path = wiki_path / rel_path
                    
                    # Ensure target directory exists
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    try:
                        # Copy file
                        shutil.copy2(item, target_path)
                        
                        # Check if file was updated
                        if target_path.exists():
                            source_mtime = item.stat().st_mtime
                            target_mtime = target_path.stat().st_mtime
                            
                            if source_mtime > target_mtime:
                                stats["updated"] += 1
                                logger.debug(f"Updated: {rel_path}")
                            else:
                                stats["copied"] += 1
                                logger.debug(f"Copied: {rel_path}")
                        else:
                            stats["copied"] += 1
                            logger.debug(f"Copied: {rel_path}")
                            
                    except Exception as e:
                        logger.error(f"Failed to copy {item}: {e}")
                        stats["errors"] += 1
        
        return stats
    
    def update_home_page(self) -> bool:
        """Update the main Home.md page with new content"""
        home_source = self.source_dir / "Home.md"
        home_wiki = self.wiki_dir / "Home.md"
        
        if not home_source.exists():
            logger.warning("Source Home.md does not exist, skipping home page update")
            return True
        
        try:
            shutil.copy2(home_source, home_wiki)
            logger.info("Home page updated")
            return True
        except Exception as e:
            logger.error(f"Failed to update home page: {e}")
            return False
    
    def git_operations(self, auto_commit: bool = True, auto_push: bool = False) -> bool:
        """Perform git operations"""
        if not self.wiki_dir.exists():
            logger.error("Wiki directory does not exist")
            return False
        
        try:
            # Change to wiki directory
            os.chdir(self.wiki_dir)
            
            # Check git status
            result = subprocess.run(["git", "status", "--porcelain"], 
                                  capture_output=True, text=True, check=True)
            
            if not result.stdout.strip():
                logger.info("No changes to commit")
                return True
            
            if auto_commit:
                # Add all changes
                subprocess.run(["git", "add", "."], check=True)
                
                # Commit changes
                commit_message = f"Auto-sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                subprocess.run(["git", "commit", "-m", commit_message], check=True)
                logger.info("Changes committed")
                
                if auto_push:
                    # Push changes
                    subprocess.run(["git", "push", "origin", "master"], check=True)
                    logger.info("Changes pushed to remote")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in git operations: {e}")
            return False
        finally:
            # Return to original directory
            os.chdir("..")
    
    def should_sync(self) -> bool:
        """Check if synchronization is needed based on config"""
        config = self.load_config()
        last_sync = config.get("last_sync")
        
        if not last_sync:
            return True
        
        # Parse last sync time
        try:
            last_sync_dt = datetime.fromisoformat(last_sync)
            hours_since_sync = (datetime.now() - last_sync_dt).total_seconds() / 3600
            sync_interval = config.get("sync_interval_hours", 24)
            
            return hours_since_sync >= sync_interval
        except Exception as e:
            logger.warning(f"Could not parse last sync time: {e}")
            return True
    
    def sync(self, force: bool = False, auto_commit: bool = True, 
             auto_push: bool = False) -> bool:
        """Main synchronization method"""
        logger.info("Starting wiki synchronization...")
        
        # Check if sync is needed
        if not force and not self.should_sync():
            logger.info("Synchronization not needed based on interval")
            return True
        
        # Check wiki repository
        if not self.check_wiki_repo():
            logger.info("Wiki repository not found, cloning...")
            if not self.clone_wiki_repo():
                return False
        
        # Load configuration
        config = self.load_config()
        
        # Backup if enabled
        if config.get("backup_enabled", True):
            self.backup_wiki()
        
        # Sync files
        stats = self.sync_files()
        logger.info(f"Sync stats: {stats}")
        
        # Update home page
        self.update_home_page()
        
        # Git operations
        if auto_commit:
            self.git_operations(auto_commit=auto_commit, auto_push=auto_push)
        
        # Update configuration
        config["last_sync"] = datetime.now().isoformat()
        self.save_config(config)
        
        # Log sync
        log_entries = self.load_sync_log()
        log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "auto_commit": auto_commit,
            "auto_push": auto_push
        })
        self.save_sync_log(log_entries)
        
        logger.info("Wiki synchronization completed successfully")
        return True
    
    def status(self) -> Dict:
        """Get synchronization status"""
        config = self.load_config()
        log_entries = self.load_sync_log()
        
        status = {
            "config": config,
            "last_sync": config.get("last_sync"),
            "sync_interval_hours": config.get("sync_interval_hours", 24),
            "total_syncs": len(log_entries),
            "wiki_repo_exists": self.check_wiki_repo(),
            "source_dir_exists": self.source_dir.exists(),
            "source_files": len(list(self.source_dir.rglob("*"))) if self.source_dir.exists() else 0
        }
        
        if log_entries:
            last_entry = log_entries[-1]
            status["last_sync_stats"] = last_entry.get("stats", {})
        
        return status

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Automated Wiki Update System")
    parser.add_argument("--force", action="store_true", 
                       help="Force synchronization regardless of interval")
    parser.add_argument("--no-commit", action="store_true",
                       help="Don't auto-commit changes")
    parser.add_argument("--auto-push", action="store_true",
                       help="Auto-push changes to remote")
    parser.add_argument("--status", action="store_true",
                       help="Show synchronization status")
    parser.add_argument("--config", action="store_true",
                       help="Show current configuration")
    
    args = parser.parse_args()
    
    updater = WikiUpdater()
    
    if args.status:
        status = updater.status()
        print(json.dumps(status, indent=2))
        return
    
    if args.config:
        config = updater.load_config()
        print(json.dumps(config, indent=2))
        return
    
    # Perform synchronization
    success = updater.sync(
        force=args.force,
        auto_commit=not args.no_commit,
        auto_push=args.auto_push
    )
    
    if success:
        logger.info("Wiki synchronization completed successfully")
        sys.exit(0)
    else:
        logger.error("Wiki synchronization failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
