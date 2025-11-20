import os
import sys
import time
import shutil
import logging

# Add project root to path
sys.path.append(os.getcwd())

from app.services.audit_logger import FERPAAuditLogger

# Configuration for test
TEST_LOG_FILE = "tests/logs/audit_test.log"
TEST_ARCHIVE_DIR = "tests/logs/archive"
MAX_BYTES = 1024  # 1KB for testing
BACKUP_COUNT = 5

def setup_test_env():
    """Clean up and recreate test directories."""
    if os.path.exists("tests/logs"):
        shutil.rmtree("tests/logs")
    os.makedirs("tests/logs", exist_ok=True)
    os.makedirs(TEST_ARCHIVE_DIR, exist_ok=True)
    
    # Set env vars for the logger
    os.environ["AUDIT_LOG_FILE"] = TEST_LOG_FILE
    os.environ["AUDIT_LOG_MAX_BYTES"] = str(MAX_BYTES)
    os.environ["AUDIT_LOG_BACKUP_COUNT"] = str(BACKUP_COUNT)
    os.environ["AUDIT_ARCHIVE_DIR"] = TEST_ARCHIVE_DIR
    os.environ["AUDIT_LOG_TO_FILE"] = "true"
    os.environ["AUDIT_LOG_STDOUT"] = "false"

def verify_rotation():
    print("Starting Log Rotation Verification...")
    setup_test_env()
    
    logger = FERPAAuditLogger(enabled=True)
    
    # Generate enough logs to trigger rotation multiple times
    # Each log entry is roughly 200-300 bytes
    print("Generating logs...")
    for i in range(50):
        logger.log_data_access(
            user_id=f"user_{i}",
            user_email=f"user_{i}@example.com",
            user_role="educator",
            school_id="school_123",
            action="view",
            purpose="Testing log rotation",
            student_id=f"student_{i}",
            data_sources_accessed=["REAL"]
        )
        # Small sleep to ensure timestamps differ slightly if needed
        # time.sleep(0.01)
    
    print("Logs generated. Waiting for background threads to finish archival...")
    time.sleep(2)  # Wait for async archival threads
    
    # Check if active log exists
    if os.path.exists(TEST_LOG_FILE):
        print(f"[OK] Active log file exists: {TEST_LOG_FILE} ({os.path.getsize(TEST_LOG_FILE)} bytes)")
    else:
        print(f"[FAIL] Active log file missing: {TEST_LOG_FILE}")
        
    # Check for archived files
    archives = os.listdir(TEST_ARCHIVE_DIR)
    gz_files = [f for f in archives if f.endswith(".gz")]
    sha_files = [f for f in archives if f.endswith(".sha256")]
    
    print(f"Found {len(gz_files)} archived .gz files")
    print(f"Found {len(sha_files)} checksum .sha256 files")
    
    if len(gz_files) > 0 and len(gz_files) == len(sha_files):
        print("[OK] Archival and checksum generation successful")
    else:
        print("[FAIL] Archival failed or checksum mismatch")
        
    # Verify content of one archive
    if gz_files:
        import gzip
        latest_gz = os.path.join(TEST_ARCHIVE_DIR, gz_files[-1])
        try:
            with gzip.open(latest_gz, 'rt') as f:
                content = f.read()
                if "user_" in content:
                    print(f"[OK] Verified content of archived log: {gz_files[-1]}")
                else:
                    print(f"[FAIL] Archived log content verification failed")
        except Exception as e:
            print(f"[FAIL] Failed to read archived log: {e}")

if __name__ == "__main__":
    verify_rotation()
