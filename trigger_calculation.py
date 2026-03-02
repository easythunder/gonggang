#!/usr/bin/env python3
"""Manually trigger free time calculation."""

import sys
import os
os.chdir('/app')
sys.path.insert(0, '/app')

from uuid import UUID
from src.lib.database import DatabaseManager
from src.services.calculation import CalculationService
from src.repositories.submission import SubmissionRepository
from src.repositories.interval import IntervalRepository
from src.repositories.free_time_result import FreeTimeResultRepository

# Initialize database
DatabaseManager.init_db()
session = DatabaseManager.get_session()

try:
    # Group ID to calculate
    group_id = UUID("ca45b776-a0a0-41a9-be99-0b3a6210f618")
    
    print(f"🔄 Triggering calculation for group {group_id}...")
    
    # Create calculation service
    calc_service = CalculationService(
        session,
        submission_repo=SubmissionRepository(session),
        interval_repo=IntervalRepository(session),
        free_time_result_repo=FreeTimeResultRepository(session)
    )
    
    # Trigger calculation
    result, error = calc_service.trigger_calculation(group_id)
    
    if error:
        print(f"❌ Calculation error: {error}")
        sys.exit(1)
    
    if result:
        print(f"✅ Calculation completed!")
        print(f"   Version: {result.version}")
        print(f"   Free time slots: {len(result.free_time_slots)}")
    else:
        print(f"⚠️  No result returned")
    
    session.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    session.rollback()
    sys.exit(1)
