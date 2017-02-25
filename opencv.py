from collections import deque

import cv2
import sys

fps = 15

d = deque([], 10*fps)  #10 segundos por 15 frames

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Unable to open camera 0")
    sys.exit()

# Define the codec and create VideoWriter object
fourcc = cv2.cv.CV_FOURCC(*'XVID')
out = cv2.VideoWriter('output.avi',fourcc, fps, (640,480))

counter = 0

while cap.isOpened():
    ret, frame = cap.read()
    if ret and (counter < 20*fps):
        #out.write(frame)
        d.append(frame)
        counter+=1
        #TODO: wait for a key
    else:
        break




# Release everything if job is finished
cap.release()
out.release()