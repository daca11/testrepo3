import time

from SimpleCV import Camera, VideoStream

secondsBuffer = 10
secondsToRecord = 60
fps = 10

# d = deque([], secondsBuffer*fps)  #10 segundos de buffer

c = Camera()
vs = VideoStream("out.avi", fps=fps)

framecount = 0

while(framecount < fps * secondsToRecord): #record for 60 sec @ 10fps
    # d.append(c.getImage())  # .save(vs)
    c.getImage().save(vs)
    framecount += 1
    time.sleep(0.1) # 1 sec = 0.1 * 10 sec TODO: adjust to match fps

# for frame in d:
#     frame.save(vs)