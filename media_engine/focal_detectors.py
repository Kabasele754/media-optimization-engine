def detect_focal_point(image):
    """Optional face-aware focal detector.

    Install requirements-ai.txt to enable OpenCV face detection. If OpenCV is
    not installed or no face is found, return (None, None) and the normal
    center crop remains in effect.
    """
    try:
        import cv2
        import numpy as np
    except Exception:
        return None, None

    rgb = image.convert('RGB')
    arr = np.asarray(rgb)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(32, 32))
    if len(faces) == 0:
        return None, None

    x1 = min(int(x) for x, y, w, h in faces)
    y1 = min(int(y) for x, y, w, h in faces)
    x2 = max(int(x + w) for x, y, w, h in faces)
    y2 = max(int(y + h) for x, y, w, h in faces)
    return ((x1 + x2) / 2 / image.width, (y1 + y2) / 2 / image.height)
