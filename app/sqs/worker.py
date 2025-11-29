import asyncio
import signal
import sys
from typing import Dict, Any
from datetime import datetime
from .notification_queue import NotificationQueueService


class NotificationWorker:
    def __init__(self, batch_size: int = 5, polling_interval: int = 10):
        self.notification_service = NotificationQueueService()
        self.batch_size = batch_size
        self.polling_interval = polling_interval
        self.running = False
        self.stats = {
            "start_time": None,
            "total_processed": 0,
            "total_successful": 0,
            "total_failed": 0,
            "total_retried": 0,
            "last_batch_time": None,
            "last_batch_size": 0
        }
    
    async def start(self):
        if not self.notification_service.enabled:
            return
        
        self.running = True
        self.stats["start_time"] = datetime.now()
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            while self.running:
                await self._process_batch()
                await asyncio.sleep(self.polling_interval)
                
        except Exception as e:
            pass
        finally:
            await self._shutdown()
    
    async def _process_batch(self):
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self.notification_service.process_queued_notifications,
                    self.batch_size
                )
                results = future.result(timeout=30)
            
            self.stats["last_batch_time"] = datetime.now()
            self.stats["last_batch_size"] = results.get("processed", 0)
            self.stats["total_processed"] += results.get("processed", 0)
            self.stats["total_successful"] += results.get("successful", 0)
            self.stats["total_failed"] += results.get("failed", 0)
            self.stats["total_retried"] += results.get("retried", 0)
            
        except Exception as e:
            self.stats["total_failed"] += 1
    
    def _signal_handler(self, signum, frame):
        self.running = False
    
    async def _shutdown(self):
        self.running = False
    
    def get_stats(self) -> Dict[str, Any]:
        runtime = None
        if self.stats["start_time"]:
            runtime = datetime.now() - self.stats["start_time"]
        
        return {
            "running": self.running,
            "start_time": self.stats["start_time"].isoformat() if self.stats["start_time"] else None,
            "runtime_seconds": runtime.total_seconds() if runtime else None,
            "batch_size": self.batch_size,
            "polling_interval": self.polling_interval,
            "total_processed": self.stats["total_processed"],
            "total_successful": self.stats["total_successful"],
            "total_failed": self.stats["total_failed"],
            "total_retried": self.stats["total_retried"],
            "last_batch_time": self.stats["last_batch_time"].isoformat() if self.stats["last_batch_time"] else None,
            "last_batch_size": self.stats["last_batch_size"],
            "success_rate": (
                self.stats["total_successful"] / max(self.stats["total_processed"], 1) * 100
                if self.stats["total_processed"] > 0 else 0
            )
        }
    
    def stop(self):
        """Stop the worker"""
        self.running = False


_worker_instance = None


def get_notification_worker(batch_size: int = 5, polling_interval: int = 10) -> NotificationWorker:
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = NotificationWorker(batch_size, polling_interval)
    return _worker_instance


async def start_background_worker(batch_size: int = 5, polling_interval: int = 10):
    worker = get_notification_worker(batch_size, polling_interval)
    await worker.start()


def stop_background_worker():
    global _worker_instance
    if _worker_instance:
        _worker_instance.stop()


async def main():
    import os
    
    batch_size = int(os.getenv('SQS_WORKER_BATCH_SIZE', '5'))
    polling_interval = int(os.getenv('SQS_WORKER_POLLING_INTERVAL', '10'))
    
    worker = NotificationWorker(batch_size, polling_interval)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    asyncio.run(main())