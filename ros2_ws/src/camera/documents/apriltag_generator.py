#!/usr/bin/env python3
import os, sys
import cv2
import numpy as np

DICT_NAME="DICT_APRILTAG_25H9"
IDS=[0]
SIZE=800
MARGIN=200

folder=os.path.dirname(os.path.abspath(__file__))
dictionary=cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICT_NAME))
count=dictionary.bytesList.shape[0]
ids=IDS

bad=[i for i in ids if i<0 or i>=count]
if bad: sys.exit(f"Invalid ids {bad}, {DICT_NAME} has ids 0 to {count-1}")

for tag_id in ids:
    if hasattr(cv2.aruco, "generateImageMarker"): tag=cv2.aruco.generateImageMarker(dictionary, tag_id, SIZE)
    else:
        tag=np.zeros((SIZE, SIZE), dtype=np.uint8)
        cv2.aruco.drawMarker(dictionary, tag_id, SIZE, tag, 1)

    tag=cv2.copyMakeBorder(tag, MARGIN, MARGIN, MARGIN, MARGIN, cv2.BORDER_CONSTANT, value=255)
    path=os.path.join(folder, f"apriltag_25h9_id{tag_id}.png")
    cv2.imwrite(path, tag)
    print(f"Saved {path} ({tag.shape[1]}x{tag.shape[0]} px)")