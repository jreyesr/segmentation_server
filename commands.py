import os
import shutil

def to_pcd(pointcloud):
    print("LAS -> PCD")
    if not pointcloud.istype(".pcd"): # only convert to PCD if it isn't already
        ret = os.system("pdal translate -i pointclouds/{} -o {}".format(pointcloud.filename, pointcloud.pcd_path))
    else: # fake successful command invocation
        ret = 0
    print("LAS -> PCD complete")
    return ret == 0

def remove_ground(pointcloud):
    print("Removing ground")
    shutil.copyfile(pointcloud.pcd_path, pointcloud.final_pcd_path)
    print("Removing ground complete")
    return True

def to_las(pointcloud):
    print("PCD -> LAS")
    ret = os.system("pdal translate -i {} -o {}".format(pointcloud.final_pcd_path, pointcloud.final_las_path))
    print("PCD -> LAS complete")
    return ret == 0

def to_potree(pointcloud, original=False):
    print("To Potree format, original={}".format(original))
    if original:
        src = pointcloud.las_path
        dst = "orig_{}".format(pointcloud.uid)
    else:
        src = pointcloud.final_las_path
        dst = pointcloud.uid
    ret = os.system("./PotreeConverter {} -o potree/pointclouds/{}".format(src, dst))
    print("To Potree format complete")
    return ret == 0