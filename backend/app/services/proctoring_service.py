"""
NexusAI Talent OS — Proctoring Service (pre-trained models, zero training data needed)
Face detection + gaze (MediaPipe) + phone detection (YOLOv8n).
Gracefully degrades to no-op if optional deps (mediapipe/ultralytics/opencv) aren't installed —
guarded by FEATURE_PROCTORING and try/except import.
"""
import asyncio, logging
import numpy as np
from app.core.config import settings

logger = logging.getLogger(__name__)

_face_detection = None
_face_mesh = None
_object_detector = None
_deps_available = True

try:
    import cv2  # noqa
except ImportError:
    _deps_available = False
    logger.warning("opencv-python-headless not installed — proctoring frame analysis disabled")


def get_face_detection():
    global _face_detection
    if _face_detection is None:
        import mediapipe as mp
        _face_detection = mp.solutions.face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=settings.FACE_DETECTION_CONFIDENCE)
    return _face_detection


def get_face_mesh():
    global _face_mesh
    if _face_mesh is None:
        import mediapipe as mp
        _face_mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=2, refine_landmarks=True,
            min_detection_confidence=0.7)
    return _face_mesh


def get_object_detector():
    global _object_detector
    if _object_detector is None:
        from ultralytics import YOLO
        _object_detector = YOLO('yolov8n.pt')
    return _object_detector


async def prewarm_proctoring_models():
    if not settings.FEATURE_PROCTORING or not _deps_available:
        return
    logger.info("Pre-warming proctoring models (MediaPipe + YOLOv8n)...")
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, get_face_detection)
        await loop.run_in_executor(None, get_object_detector)
        logger.info("Proctoring models ready")
    except Exception as exc:
        logger.warning(f"Proctoring pre-warm failed: {exc}")


class FrameAnalyzer:
    async def analyze(self, frame_bytes: bytes, interview_id: str) -> list[dict]:
        if not _deps_available:
            return []
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._analyze_sync, frame_bytes)

    def _analyze_sync(self, frame_bytes: bytes) -> list[dict]:
        import cv2
        events = []
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return events
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face_events = self._check_faces(rgb)
        events.extend(face_events)
        if not any(e["event_type"] in ("FACE_ABSENT", "MULTIPLE_FACES") for e in face_events):
            events.extend(self._check_gaze(rgb))
        events.extend(self._check_objects(frame))
        return events

    def _check_faces(self, rgb) -> list[dict]:
        events = []
        try:
            fd = get_face_detection()
            results = fd.process(rgb)
            if not results.detections:
                events.append({"event_type": "FACE_ABSENT", "severity": "medium",
                    "confidence": 0.95, "metadata": {"face_count": 0}})
            elif len(results.detections) >= settings.MULTIPLE_FACES_THRESHOLD:
                events.append({"event_type": "MULTIPLE_FACES", "severity": "high",
                    "confidence": min(d.score[0] for d in results.detections),
                    "metadata": {"face_count": len(results.detections)}})
        except Exception as exc:
            logger.debug(f"Face check error: {exc}")
        return events

    def _check_gaze(self, rgb) -> list[dict]:
        events = []
        try:
            fm = get_face_mesh()
            results = fm.process(rgb)
            if not results.multi_face_landmarks:
                return events
            lm = results.multi_face_landmarks[0].landmark
            nose_x, left_x, right_x = lm[4].x, lm[33].x, lm[263].x
            left_iris_x, right_iris_x = lm[468].x, lm[473].x
            left_ratio = (left_iris_x - left_x) / max(abs(nose_x - left_x), 0.001)
            right_ratio = (right_iris_x - nose_x) / max(abs(right_x - nose_x), 0.001)
            avg_ratio = (left_ratio + right_ratio) / 2
            if avg_ratio < 0.35 or avg_ratio > 0.65:
                events.append({"event_type": "GAZE_AWAY", "severity": "low", "confidence": 0.7,
                    "metadata": {"direction": "right" if avg_ratio > 0.65 else "left",
                                 "ratio": round(avg_ratio, 3)}})
        except Exception as exc:
            logger.debug(f"Gaze check error: {exc}")
        return events

    def _check_objects(self, bgr) -> list[dict]:
        events = []
        try:
            detector = get_object_detector()
            results = detector(bgr, verbose=False, conf=0.5)
            for result in results:
                for box in result.boxes:
                    name = result.names[int(box.cls[0])]
                    if name == "cell phone":
                        events.append({"event_type": "PHONE_DETECTED", "severity": "high",
                            "confidence": float(box.conf[0]),
                            "metadata": {"object": name, "bbox": box.xyxy[0].tolist()}})
        except Exception as exc:
            logger.debug(f"Object detection error: {exc}")
        return events


frame_analyzer = FrameAnalyzer()


async def update_session_risk(interview_id: str, new_events: list[dict]):
    weights = {"critical": 0.4, "high": 0.2, "medium": 0.1, "low": 0.05}
    delta = sum(weights.get(e["severity"], 0.05) for e in new_events)
    from app.core.database import AsyncSessionLocal
    from app.models.models import Interview
    from sqlalchemy import update
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Interview).where(Interview.id == interview_id)
            .values(proctoring_risk_score=Interview.proctoring_risk_score + delta)
        )
        await db.commit()
