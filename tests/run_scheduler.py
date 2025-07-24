#!/usr/bin/env python3
"""
Standalone scheduler service for email reports
This can be run independently of the main FastAPI application
"""
import sys
import os
import asyncio
import logging
import signal
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from booking.scheduler import report_scheduler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SchedulerService:
    """Standalone scheduler service"""
    
    def __init__(self):
        self.running = False
    
    async def start(self):
        """Start the scheduler service"""
        logger.info("Starting Email Report Scheduler Service")
        logger.info(f"Started at: {datetime.now()}")
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Start the report scheduler
            await report_scheduler.start()
            self.running = True
            
            logger.info("✅ Scheduler service started successfully")
            logger.info("📧 Email reports will be sent according to configured schedule")
            logger.info("🔄 Checking every 10 minutes for scheduled reports")
            logger.info("⏹️  Press Ctrl+C to stop")
            
            # Keep the service running
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in scheduler service: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the scheduler service"""
        logger.info("Stopping scheduler service...")
        await report_scheduler.stop()
        logger.info("✅ Scheduler service stopped")


async def main():
    """Main function"""
    service = SchedulerService()
    await service.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScheduler service stopped by user")
    except Exception as e:
        print(f"Error running scheduler service: {e}")
        sys.exit(1)