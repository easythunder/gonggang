"""API endpoints for submission management."""
import logging
import time
from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from uuid import UUID
from src.lib.database import DatabaseManager
from src.services.group import GroupService
from src.services.submission import (
    SubmissionService,
    DuplicateSubmissionError,
    SubmissionError,
    EverytimeSubmissionParseError,
)
from src.services.ocr import OCRWrapper, OCRTimeoutError, OCRFailedError
from src.services.interval_extractor import IntervalExtractor, IntervalExtractionError
from src.services.image_pipeline import TimetableImagePipeline, PipelineResult
from src.services.timetable_detector import TimetableDetectionError

logger = logging.getLogger(__name__)

# Global database manager (initialized in main.py)
db_manager: DatabaseManager = None


def _parse_group_uuid(group_id: str) -> UUID:
    """Parse and validate group_id string to UUID."""
    try:
        return UUID(group_id)
    except (ValueError, TypeError) as exc:
        logger.warning(f"Invalid group_id format: {group_id}")
        raise HTTPException(
            status_code=422,
            detail="Invalid group_id format (must be valid UUID)",
        ) from exc


def _validate_nickname(nickname: str) -> None:
    """Validate nickname format and length."""
    if not nickname or len(nickname) > 50:
        raise HTTPException(
            status_code=422,
            detail="Invalid nickname (1-50 characters)",
        )


def _get_group_or_raise(group_uuid: UUID):
    """Get group and raise HTTPException if not found/expired."""
    session = db_manager.get_session()
    group_service = GroupService(session)
    group, error_code = group_service.get_group(group_uuid)

    if error_code or not group:
        if error_code == "GROUP_EXPIRED":
            raise HTTPException(status_code=410, detail="Group has expired")
        raise HTTPException(status_code=404, detail="Group not found")

    return group


def _build_submission_response(
    submission,
    nickname: str,
    group_uuid: UUID,
    interval_count: int,
    total_time_ms: float,
    ocr_time_ms: float,
) -> JSONResponse:
    """Build standardized submission response payload and headers."""
    response_data = {
        "submission_id": str(submission.id),
        "nickname": nickname,
        "group_id": str(group_uuid),
        "status": submission.status.value if hasattr(submission.status, "value") else str(submission.status),
        "interval_count": interval_count,
        "created_at": submission.submitted_at.isoformat() if hasattr(submission, "submitted_at") else None,
    }

    response = JSONResponse(status_code=201, content=response_data)
    response.headers["X-Response-Time"] = f"{total_time_ms:.0f}"
    response.headers["X-Ocr-Time"] = f"{ocr_time_ms:.0f}"
    response.headers["X-Interval-Count"] = str(interval_count)
    return response


def set_db_manager(manager: DatabaseManager):
    """Set the global database manager."""
    global db_manager
    db_manager = manager


def get_submission_service() -> SubmissionService:
    """Dependency: Get submission service with database session."""
    session = db_manager.get_session()
    return SubmissionService(session)


def get_ocr_wrapper() -> OCRWrapper:
    """Dependency: Get OCR wrapper."""
    return OCRWrapper(library="tesseract", timeout_seconds=3)


def get_interval_extractor(group_id: UUID) -> IntervalExtractor:
    """Dependency: Get interval extractor with group's display unit."""
    session = db_manager.get_session()
    group_service = GroupService(session)
    group, error_code = group_service.get_group(group_id)
    
    if error_code or not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return IntervalExtractor(display_unit_minutes=group.display_unit_minutes)


# Create router
router = APIRouter(prefix="/api", tags=["submissions"])


class SubmitScheduleRequest:
    """Request model for schedule submission."""
    group_id: UUID
    nickname: str
    image: UploadFile


class SubmitScheduleResponse:
    """Response model for schedule submission."""
    submission_id: str
    nickname: str
    group_id: str
    status: str
    interval_count: int
    created_at: str
    ocr_confidence: Optional[float] = None


@router.post("/submissions", status_code=201, response_class=JSONResponse)
async def submit_schedule(
    group_id: str = Form(...),
    nickname: str = Form(...),
    image: UploadFile = File(...),
    _submission_service: SubmissionService = Depends(get_submission_service),
    _ocr_wrapper: OCRWrapper = Depends(get_ocr_wrapper),
):
    """Submit a schedule image for free time calculation.
    
    Flow:
    1. Validate group exists and not expired
    2. Parse image with OCR (timeout: 3s)
    3. Extract intervals and normalize
    4. Store submission in database
    5. Update group's last_activity_at (extends expiration)
    6. Return submission details
    
    Request:
    - group_id (string): UUID of target group
    - nickname (string): Participant display name
    - image (file): Schedule screenshot
    
    Response (201):
    - submission_id: UUID of created submission
    - nickname: Submitted nickname
    - group_id: Group UUID
    - status: 'SUCCESS' or 'FAILED'
    - interval_count: Number of free time intervals extracted
    - created_at: ISO timestamp
    - X-Response-Time: Total response time in milliseconds
    - X-Ocr-Time: OCR processing time in milliseconds
    
    Error Responses:
    - 404: Group not found or expired
    - 408: OCR timeout exceeded (>3s)
    - 409: Duplicate submission (nickname already exists)
    - 422: Invalid input (group_id not UUID, nickname too long)
    - 500: Server error
    
    Note: Image is processed in memory only - never persisted to disk.
    """
    start_time = time.time()
    ocr_start_time = None
    ocr_end_time = None

    try:
        # Parse and validate group_id
        group_uuid = _parse_group_uuid(group_id)

        # Validate nickname
        _validate_nickname(nickname)

        # Validate file
        if not image or image.size == 0:
            raise HTTPException(
                status_code=422,
                detail="Invalid image file"
            )

        # Read image bytes into memory (no disk storage)
        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(
                status_code=400,
                detail="Empty image file"
            )

        logger.info(
            f"Processing submission: group={group_uuid}, nickname={nickname}, "
            f"image_size={len(image_bytes)} bytes"
        )

        # Get group and verify not expired
        group = _get_group_or_raise(group_uuid)

        # Parse image with OCR
        logger.debug(f"Starting OCR parsing ({_ocr_wrapper.timeout_seconds}s timeout)")
        ocr_start_time = time.time()

        try:
            ocr_text = _ocr_wrapper.parse_image(image_bytes)
            ocr_end_time = time.time()
            logger.info(f"OCR completed: {len(ocr_text)} characters extracted")

        except OCRTimeoutError:
            logger.error("OCR timeout exceeded")
            raise HTTPException(
                status_code=408,
                detail="OCR processing timeout exceeded (>3s). Please try again."
            )
        except OCRFailedError as e:
            logger.warning(f"OCR parsing failed: {e}")
            # Still create submission with FAILED status
            ocr_text = ""
            ocr_end_time = time.time()

        # Extract intervals from OCR text
        interval_extractor = IntervalExtractor(
            display_unit_minutes=group.display_unit_minutes
        )

        try:
            if ocr_text:
                intervals = interval_extractor.extract_intervals_from_text(ocr_text)
                ocr_success = True
            else:
                intervals = []
                ocr_success = False

            logger.info(f"Extracted {len(intervals)} intervals")

        except IntervalExtractionError as e:
            logger.warning(f"Interval extraction failed: {e}")
            intervals = []
            ocr_success = False

        # Create submission in database
        try:
            submission, error_code = _submission_service.create_submission(
                group_id=group_uuid,
                nickname=nickname,
                intervals=intervals,
                ocr_success=ocr_success,
                error_reason="OCR parsing failed" if not ocr_success else None,
            )
            
            if error_code:
                raise HTTPException(status_code=500, detail=f"Failed to create submission: {error_code}")

            # Update group's last_activity_at (extends expiration)
            _submission_service.update_group_last_activity(group_uuid)

            logger.info(
                f"Created submission {submission.id} with {len(intervals)} intervals"
            )
            
            # Trigger calculation explicitly (should already be called in service, but ensuring it happens)
            if submission.status.value == "SUCCESS":
                try:
                    from src.services.calculation import CalculationService
                    calc_service = CalculationService(db_manager.get_session())
                    result, calc_error = calc_service.trigger_calculation(group_uuid)
                    if calc_error:
                        logger.warning(f"Calculation error for group {group_uuid}: {calc_error}")
                    else:
                        logger.info(f"Calculation completed for group {group_uuid}, version: {result.version if result else 'N/A'}")
                except Exception as calc_exc:
                    logger.error(f"Failed to trigger calculation: {calc_exc}", exc_info=True)
                    # Don't fail the submission if calculation fails - user still got their submission saved

        except DuplicateSubmissionError:
            raise HTTPException(
                status_code=409,
                detail=f"Nickname '{nickname}' already submitted for this group"
            )
        except SubmissionError as e:
            logger.error(f"Submission creation failed: {e}")
            raise HTTPException(status_code=500, detail="Submission storage failed")

        # Calculate timing
        total_time_ms = (time.time() - start_time) * 1000
        ocr_time_ms = (ocr_end_time - ocr_start_time) * 1000 if ocr_start_time else 0

        logger.info(
            f"Submission completed: {submission.id} "
            f"({total_time_ms:.0f}ms total, {ocr_time_ms:.0f}ms OCR)"
        )

        # Return response with timing headers
        return _build_submission_response(
            submission=submission,
            nickname=nickname,
            group_uuid=group_uuid,
            interval_count=len(intervals),
            total_time_ms=total_time_ms,
            ocr_time_ms=ocr_time_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in submit_schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/submissions/everytime-link", status_code=201, response_class=JSONResponse)
async def submit_schedule_by_everytime_link(
    group_id: str = Form(...),
    nickname: str = Form(...),
    everytime_url: str = Form(...),
    _submission_service: SubmissionService = Depends(get_submission_service),
):
    """Submit schedule by parsing public Everytime timetable link."""
    start_time = time.time()

    try:
        group_uuid = _parse_group_uuid(group_id)
        _validate_nickname(nickname)

        if not everytime_url:
            raise HTTPException(status_code=422, detail="everytime_url is required")

        group = _get_group_or_raise(group_uuid)

        submission, intervals = _submission_service.create_submission_from_everytime_link(
            group_id=group_uuid,
            nickname=nickname,
            everytime_url=everytime_url,
            display_unit_minutes=group.display_unit_minutes,
        )

        _submission_service.update_group_last_activity(group_uuid)

        total_time_ms = (time.time() - start_time) * 1000

        return _build_submission_response(
            submission=submission,
            nickname=nickname,
            group_uuid=group_uuid,
            interval_count=len(intervals),
            total_time_ms=total_time_ms,
            ocr_time_ms=0,
        )

    except DuplicateSubmissionError:
        raise HTTPException(
            status_code=409,
            detail=f"Nickname '{nickname}' already submitted for this group",
        )
    except EverytimeSubmissionParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntervalExtractionError as exc:
        raise HTTPException(status_code=422, detail=f"Interval extraction failed: {exc}") from exc
    except SubmissionError:
        raise HTTPException(status_code=500, detail="Submission storage failed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in submit_schedule_by_everytime_link: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/submissions/{submission_id}", status_code=200)
async def get_submission(
    submission_id: str,
    _submission_service: SubmissionService = Depends(get_submission_service),
):
    """Retrieve submission details.
    
    Returns:
    - submission_id: UUID
    - group_id: UUID
    - nickname: Participant nickname
    - status: 'SUCCESS', 'FAILED', or 'PENDING'
    - interval_count: Number of intervals
    - submitted_at: ISO timestamp
    - error_reason: If status is FAILED
    """
    try:
        submission_uuid = UUID(submission_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Invalid submission_id format")

    try:
        submission = _submission_service.get_submission(submission_uuid)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        intervals = _submission_service.get_submission_intervals(submission_uuid)

        response_data = {
            "submission_id": str(submission.id),
            "group_id": str(submission.group_id),
            "nickname": submission.nickname,
            "status": submission.status.value if hasattr(submission.status, 'value') else str(submission.status),
            "interval_count": len(intervals),
            "submitted_at": submission.submitted_at.isoformat() if hasattr(submission, 'submitted_at') else None,
        }

        if submission.error_reason:
            response_data["error_reason"] = submission.error_reason

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve submission: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/groups/{group_id}/submissions", status_code=200)
async def list_group_submissions(
    group_id: str,
    _submission_service: SubmissionService = Depends(get_submission_service),
):
    """List all submissions for a group.
    
    Returns:
    - submissions: Array of submission objects
    - total_count: Total submissions
    - successful_count: Submissions with status SUCCESS
    """
    try:
        group_uuid = UUID(group_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Invalid group_id format")

    try:
        submissions = _submission_service.get_group_submissions(group_uuid)
        successful_count = _submission_service.get_successful_count(group_uuid)

        submissions_data = [
            {
                "submission_id": str(sub.id),
                "nickname": sub.nickname,
                "status": sub.status.value if hasattr(sub.status, 'value') else str(sub.status),
                "submitted_at": sub.submitted_at.isoformat() if hasattr(sub, 'submitted_at') else None,
            }
            for sub in submissions
        ]

        return {
            "submissions": submissions_data,
            "total_count": len(submissions),
            "successful_count": successful_count,
        }

    except Exception as e:
        logger.error(f"Failed to list submissions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# YOLO-based Image Processing Pipeline
# ============================================================

@router.post("/submissions/image-yolo", status_code=201, response_class=JSONResponse)
async def submit_schedule_with_yolo(
    group_id: str = Form(...),
    nickname: str = Form(...),
    image: UploadFile = File(...),
    _submission_service: SubmissionService = Depends(get_submission_service),
):
    """Submit schedule image using YOLO detection pipeline.
    
    Pipeline:
    1. 🖼️  Image decoding
    2. 🔍 YOLO timetable detection
    3. ✂️  Bounding box extraction and cropping
    4. 📖 OCR text extraction
    5. 📍 Coordinate-based schedule generation
    
    Request:
    - group_id: UUID of target group
    - nickname: Participant name
    - image: Schedule screenshot
    
    Response:
    - submission_id: UUID
    - schedule: Extracted [day, start, end, class_name]
    - metadata: Detection details and coordinates
    - status: "success" or "error"
    
    Status codes:
    - 201: Success
    - 404: Group not found
    - 409: Duplicate nickname
    - 422: Invalid input
    - 500: Server error
    """
    start_time = time.time()
    
    try:
        # Validate inputs
        group_uuid = _parse_group_uuid(group_id)
        _validate_nickname(nickname)
        
        if not image or image.size == 0:
            raise HTTPException(status_code=422, detail="Invalid image file")
        
        # Read image bytes
        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Empty image file")
        
        # Get group
        group = _get_group_or_raise(group_uuid)
        
        logger.info(f"Processing image with YOLO: group={group_uuid}, nickname={nickname}")
        
        # Initialize pipeline
        try:
            pipeline = TimetableImagePipeline(
                yolo_model_path=None,  # Use default YOLOv8n
                ocr_timeout=5,
                detection_confidence=0.5
            )
        except TimetableDetectionError as e:
            logger.error(f"Pipeline initialization failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Pipeline initialization error: {str(e)}"
            )
        
        # Process image through pipeline
        logger.info("Running YOLO-based image processing pipeline...")
        pipeline_result: PipelineResult = pipeline.process(
            image_bytes,
            display_unit_minutes=group.display_unit_minutes,
            save_crop=True
        )
        
        if not pipeline_result.success:
            logger.warning(f"Pipeline failed: {pipeline_result.error_message}")
            raise HTTPException(
                status_code=422,
                detail=f"Image processing failed: {pipeline_result.error_message}"
            )
        
        logger.info(f"Pipeline successful: extracted {len(pipeline_result.schedule)} classes")
        
        # Convert schedule to intervals using interval extractor
        if pipeline_result.schedule:
            # Schedule format: [{'day': str, 'start': str, 'end': str, ...}]
            extractor = IntervalExtractor(display_unit_minutes=group.display_unit_minutes)
            
            try:
                # Convert to IntervalData format
                interval_data_list = []
                for item in pipeline_result.schedule:
                    try:
                        day_idx = 0 if item['day'] == '월' else \
                                  1 if item['day'] == '화' else \
                                  2 if item['day'] == '수' else \
                                  3 if item['day'] == '목' else \
                                  4 if item['day'] == '금' else \
                                  5 if item['day'] == '토' else 6
                        
                        start_h, start_m = map(int, item['start'].split(':'))
                        end_h, end_m = map(int, item['end'].split(':'))
                        
                        start_min = start_h * 60 + start_m
                        end_min = end_h * 60 + end_m
                        
                        interval_data_list.append((day_idx, start_min, end_min))
                    except Exception as e:
                        logger.warning(f"Failed to parse schedule item {item}: {e}")
                        continue
                
                intervals = interval_data_list
            except Exception as e:
                logger.error(f"Interval extraction failed: {e}")
                intervals = []
        else:
            intervals = []
        
        # Create submission in database
        try:
            submission, error_code = _submission_service.create_submission(
                group_id=group_uuid,
                nickname=nickname,
                intervals=intervals,
                ocr_success=pipeline_result.success,
                error_reason=None if pipeline_result.success else pipeline_result.error_message,
            )
            
            if error_code:
                raise HTTPException(status_code=500, detail=f"Failed to create submission: {error_code}")
            
            _submission_service.update_group_last_activity(group_uuid)
            
            logger.info(f"Submission created: {submission.id} with {len(intervals)} intervals")
            
            # Trigger calculation
            if submission.status.value == "SUCCESS":
                try:
                    from src.services.calculation import CalculationService
                    calc_service = CalculationService(db_manager.get_session())
                    result, calc_error = calc_service.trigger_calculation(group_uuid)
                    if calc_error:
                        logger.warning(f"Calculation error: {calc_error}")
                except Exception as calc_exc:
                    logger.error(f"Calculation error: {calc_exc}")
        
        except DuplicateSubmissionError:
            raise HTTPException(
                status_code=409,
                detail=f"Nickname '{nickname}' already submitted for this group"
            )
        except SubmissionError as e:
            logger.error(f"Submission creation failed: {e}")
            raise HTTPException(status_code=500, detail="Submission storage failed")
        
        # Build response
        total_time_ms = (time.time() - start_time) * 1000
        
        response_data = {
            "submission_id": str(submission.id),
            "nickname": nickname,
            "group_id": str(group_uuid),
            "status": submission.status.value if hasattr(submission.status, "value") else str(submission.status),
            "interval_count": len(intervals),
            "created_at": submission.submitted_at.isoformat() if hasattr(submission, "submitted_at") else None,
            "extracted_schedule": pipeline_result.schedule,
            "metadata": {
                **pipeline_result.metadata,
                "pipeline_status": "success",
                "cell_detections": pipeline_result.cell_count,
                "ocr_text_preview": pipeline_result.ocr_text[:200] if pipeline_result.ocr_text else None,
            }
        }
        
        response = JSONResponse(status_code=201, content=response_data)
        response.headers["X-Response-Time"] = f"{total_time_ms:.0f}"
        response.headers["X-Pipeline-Success"] = "true"
        response.headers["X-Cell-Count"] = str(pipeline_result.cell_count)
        
        return response
    
    except DuplicateSubmissionError:
        raise HTTPException(
            status_code=409,
            detail=f"Nickname '{nickname}' already submitted for this group"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in submit_schedule_with_yolo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

