"""
Scheduler for HADES background tasks.

This module handles scheduling of background tasks like:
- Version synchronization
- Change compaction
- Old version cleanup
- Incremental training data generation
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.utils.logger import get_logger
from src.utils.version_sync import version_sync
from src.ecl.learner import ecl

logger = get_logger(__name__)


class TaskScheduler:
    """Scheduler for background tasks."""
    
    def __init__(self):
        """Initialize the task scheduler."""
        self.running = False
        self.tasks = []
        self.thread = None
    
    def add_task(
        self, 
        name: str, 
        func: Callable, 
        interval_seconds: int,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict] = None,
        run_on_start: bool = False
    ) -> None:
        """
        Add a task to the scheduler.
        
        Args:
            name: Task name
            func: Function to call
            interval_seconds: Interval between executions in seconds
            args: Optional positional arguments for the function
            kwargs: Optional keyword arguments for the function
            run_on_start: Whether to run the task immediately on start
        """
        task = {
            "name": name,
            "func": func,
            "interval": interval_seconds,
            "last_run": None if run_on_start else datetime.now(),
            "args": args or (),
            "kwargs": kwargs or {},
            "run_on_start": run_on_start
        }
        
        self.tasks.append(task)
        logger.info(f"Added task '{name}' with interval {interval_seconds} seconds")
    
    def start(self) -> None:
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Task scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        logger.info("Task scheduler stopped")
    
    def _run(self) -> None:
        """Run the scheduler loop."""
        while self.running:
            now = datetime.now()
            
            for task in self.tasks:
                # Skip if the task has been run recently
                if (task["last_run"] is not None and 
                    (now - task["last_run"]).total_seconds() < task["interval"]):
                    continue
                
                # Run the task
                try:
                    logger.info(f"Running task '{task['name']}'")
                    task["func"](*task["args"], **task["kwargs"])
                    task["last_run"] = now
                    logger.info(f"Task '{task['name']}' completed")
                except Exception as e:
                    logger.error(f"Error in task '{task['name']}': {e}")
            
            # Sleep for a short time to avoid busy-waiting
            time.sleep(10)


# Task implementations

def version_maintenance_task() -> None:
    """Perform version maintenance tasks."""
    logger.info("Running version maintenance task")
    
    # Step 1: Compact old changes
    compact_result = version_sync.compact_changes(
        older_than_days=30,
        changes_threshold=100
    )
    
    if compact_result.get("success", False):
        logger.info(f"Compacted {compact_result.get('compacted_entities', 0)} entities with changes")
    else:
        logger.error(f"Error compacting changes: {compact_result.get('error')}")
    
    # Step 2: Clean up very old versions
    cleanup_result = version_sync.cleanup_old_versions(
        retention_days=90
    )
    
    if cleanup_result.get("success", False):
        logger.info(f"Removed {cleanup_result.get('removed_logs', 0)} old change logs")
    else:
        logger.error(f"Error cleaning up old versions: {cleanup_result.get('error')}")


def incremental_training_task() -> None:
    """Generate incremental training data from recent changes."""
    logger.info("Running incremental training data generation task")
    
    # Process unprocessed changes and generate training data
    result = ecl.process_unprocessed_changes()
    
    if result.get("success", False):
        logger.info(f"Generated training data with {result.get('training_examples', 0)} examples")
    else:
        logger.error(f"Error generating training data: {result.get('error')}")


# Create a global scheduler instance and configure tasks
scheduler = TaskScheduler()

# Add version maintenance task (daily)
scheduler.add_task(
    name="version_maintenance",
    func=version_maintenance_task,
    interval_seconds=24 * 60 * 60,  # Daily
    run_on_start=False
)

# Add incremental training task (hourly)
scheduler.add_task(
    name="incremental_training",
    func=incremental_training_task,
    interval_seconds=60 * 60,  # Hourly
    run_on_start=True
)


def start_scheduler() -> None:
    """Start the task scheduler."""
    scheduler.start()


def stop_scheduler() -> None:
    """Stop the task scheduler."""
    scheduler.stop() 