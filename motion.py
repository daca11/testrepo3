import os

MOTION_ROOT_DIR="/home/pi/motionfiles"
CAMERAS=2

"""
    Moves all *.avi files of each camera into a directory
    named like the first video in the directory of that camera
"""
def archiveFiles():
    for num_cam in xrange(1,CAMERAS+1):
        cam_dir = MOTION_ROOT_DIR + "/cam" + str(num_cam)
        new_dir = ""
        for file in sorted(os.listdir(cam_dir)):
            #file = only filename+ext
            if file.endswith(".avi"):
                    if new_dir == "":
                        filename, extension = os.path.splitext(file)
                        new_dir = cam_dir + "/" + filename
                        os.mkdir(new_dir) #TODO: check if exists...
                    print "rename " + cam_dir + "/" + file
                    print "to " + new_dir + "/" + file
                    os.rename(cam_dir + "/" + file, new_dir + "/" + file)


