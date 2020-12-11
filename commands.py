import os

def to_pcd(pointcloud):
    print("LAS -> PCD")
    if not pointcloud.istype(".pcd"): # only convert to PCD if it isn't already
        ret = os.system("pdal translate -i pointclouds/{} -o {}".format(pointcloud.filename, pointcloud.pcd_path))
    else: # fake successful command invocation
        ret = 0
    print("LAS -> PCD complete")
    return ret == 0

def remove_ground(pointcloud):
    import time
    print("removing ground")
    time.sleep(3)
    print("removing ground complete")
    return True

def to_las(pointcloud):
    import time
    print("PCD -> LAS")
    time.sleep(1)
    print("PCD -> LAS complete")
    return True