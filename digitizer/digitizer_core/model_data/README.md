# Committed inference models

The convention (picked 2026-08-04, the YuNet wiring slice): small inference
model files the digitizer loads at runtime are COMMITTED here, next to the
code that loads them — the same shape as the sibling `chart_data/` convention
for committed data files. "Small" means a couple hundred KB; anything at
rembg scale (178 MB) does not belong in git and gets a download-cache policy
instead when it lands.

Every model gets a row here (source URL, sha256, license), and its loader
must verify the sha256 before use (see `stage1_photo_prep.
face_detector_unavailable_reason`) — a corrupted or wrong-version file must
degrade to the documented no-op, never feed garbage weights.

| File | What | Source | sha256 | License |
|---|---|---|---|---|
| `face_detection_yunet_2023mar.onnx` (232,589 bytes) | YuNet face detection (photo plan §2 row 2 — face priors), loaded by `cv2.FaceDetectorYN` via `stage1_photo_prep.detect_faces_seam` | opencv/opencv_zoo `models/face_detection_yunet/`, fetched via the LFS media endpoint `https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx` (the plain raw URLs serve a 403 / the LFS pointer — probe record: `docs/photo-prep-deps-probe-2026-08-04.md` §3) | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` (matches the upstream LFS pointer's oid; re-verified at every load) | MIT (the opencv_zoo YuNet model directory's own LICENSE) |
