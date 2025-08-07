import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional

from config import LoggingConfig


def setup_logging(config: LoggingConfig) -> logging.Logger:
    """Set up logging with rotation based on configuration."""
    
    # Create logs directory if it doesn't exist
    log_path = Path(config.file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('youtube_downloader')
    logger.setLevel(getattr(logging, config.level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=config.file_path,
        maxBytes=config.max_file_size_mb * 1024 * 1024,  # Convert MB to bytes
        backupCount=config.backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, config.level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, config.level.upper()))
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Prevent logging from propagating to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a child logger for a specific module."""
    base_logger = logging.getLogger('youtube_downloader')
    if name:
        return base_logger.getChild(name)
    return base_logger


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger instance for this class."""
        class_name = self.__class__.__name__
        return get_logger(class_name.lower())


def log_function_call(func):
    """Decorator to log function calls with arguments and results."""
    def wrapper(*args, **kwargs):
        logger = get_logger('function_calls')
        func_name = func.__name__
        
        # Log function entry
        logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func_name} failed with error: {e}")
            raise
    
    return wrapper


def log_performance(func):
    """Decorator to log function execution time."""
    import time
    
    def wrapper(*args, **kwargs):
        logger = get_logger('performance')
        func_name = func.__name__
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func_name} executed in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func_name} failed after {execution_time:.2f} seconds: {e}")
            raise
    
    return wrapper