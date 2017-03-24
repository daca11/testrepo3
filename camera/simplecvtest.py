import time

from SimpleCV import Camera, VideoStream
c = Camera()
vs = VideoStream("out.avi", fps=10)

framecount = 0
while(framecount < 10 * 60): #record for 60 sec @ 10fps
    c.getImage().save(vs)
    framecount += 1
    time.sleep(0.1) # 1 sec = 0.1 * 10 sec