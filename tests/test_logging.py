#!/usr/bin/env python3
"""
Test script to verify logging functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.booking.logging_config import setup_logging, get_logger, log_with_context
from src.booking.database import SessionLocal
from src.booking import models
import logging

# Setup logging
setup_logging()
logger = get_logger("test")

def test_logging():
    """Test various logging scenarios"""
    print("Testing logging functionality...")
    
    # Test basic logging
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # Test logging with context
    log_with_context(
        logger, logging.INFO,
        "This is a message with context",
        user_id=1,
        extra_data={"test_key": "test_value", "number": 42}
    )
    
    # Test logging with exception
    try:
        raise ValueError("This is a test exception")
    except Exception as e:
        logger.error("Caught an exception", exc_info=True)
    
    print("Logging tests completed. Checking database...")
    
    # Check database for logs
    db = SessionLocal()
    try:
        log_count = db.query(models.ApplicationLog).count()
        print(f"Total logs in database: {log_count}")
        
        # Get recent logs
        recent_logs = db.query(models.ApplicationLog).order_by(
            models.ApplicationLog.timestamp.desc()
        ).limit(5).all()
        
        print("\nRecent logs:")
        for log in recent_logs:
            print(f"  {log.timestamp} [{log.level}] {log.logger_name}: {log.message}")
            if log.extra_data:
                print(f"    Extra data: {log.extra_data}")
    finally:
        db.close()

if __name__ == "__main__":
    test_logging()