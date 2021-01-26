import glob
import json
import os
import subprocess
import shutil
import platform
import shapefile
import concurrent.futures

def _call(command):
    plat = platform.system()
    assert (plat in ("Linux, Windows")), "OS {} not supported".format(plat)
    if plat == "Windows":
        return os.system("ubuntu2004 run {}".format(command.replace('"', '\\"')))
    elif plat == "Linux":
        return os.system(command)

def _call_get_output(command):
    plat = platform.system()
    assert (plat in ("Linux, Windows")), "OS {} not supported".format(plat)
    try:
        if plat == "Windows":
            return subprocess.check_output(["ubuntu2004", "run"] + command)
        elif plat == "Linux":
            return subprocess.check_output(command)
    except subprocess.CalledProcessError as err:
        return ""

def to_pcd(pointcloud):
    print("LAS -> PCD")
    if not pointcloud.istype(".pcd"): # only convert to PCD if it isn't already
        ret = _call("pdal translate -i pointclouds/{} -o {}".format(pointcloud.filename, pointcloud.pcd_path))
    else: # fake successful command invocation
        ret = 0
    print("LAS -> PCD complete")
    return ret == 0

def remove_ground(pointcloud):
    print("Removing ground")
    ret = _call("pdal translate -i pointclouds/{} -o {} --json pdal_a.json".format(pointcloud.filename, pointcloud.pcd_path_a))
    print("Removing ground complete")
    return ret == 0
    
def segment(pointcloud):
    print("Segmenting objects")
    ret = _call("./cluster_extraction -i {} -o {}".format(pointcloud.pcd_path_a, pointcloud.final_pcd_path))
    print("Segmenting objects complete")
    return ret == 0

def to_las(pointcloud):
    print("PCD -> LAS")
    ret = _call('pdal translate -i {} -o {} --writers.las.extra_dims="ClusterID=int"'.format(pointcloud.final_pcd_path, pointcloud.final_las_path))
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
    ret = _call("LD_LIBRARY_PATH=$(pwd)/PotreeConverterLibs ./PotreeConverter {} -o potree/pointclouds/{}".format(src, dst))
    print("To Potree format complete")
    return ret == 0
    
def split_parts(pointcloud):
    print("Creating individual pointclouds")
    os.makedirs("pointclouds/parts/{}".format(pointcloud.uid))
    ret = _call('pdal translate -i {} -o pointclouds/parts/{}/#.las --json split_ids.json --readers.las.extra_dims="ClusterID=int"'.format(pointcloud.final_las_path, pointcloud.uid))
    print("Creating individual pointclouds complete")
    return ret == 0
    
def get_proj4_string(pointcloud):
    output = _call_get_output(["pdal", "info", "--metadata", "pointclouds/{}".format(pointcloud.filename)])
    info = json.loads(output)["metadata"]["srs"]["proj4"]
    return info

def get_bounds(pointcloud):
    def _get_bound(subpc):
        # out = _call_get_output(["pdal", "info", subpc, "--boundary"])
        out = _call_get_output(["pdal", "info", subpc, "--metadata"])
        out = json.loads(out)
        minx, maxx, miny, maxy = out["metadata"]["minx"], out["metadata"]["maxx"], out["metadata"]["miny"], out["metadata"]["maxy"]
        ret = { "type": "Polygon", "coordinates": [ [
            [ minx, miny ],
            [ minx, maxy ],
            [ maxx, maxy ],
            [ maxx, miny ],
            [ minx, miny ] # last coord must be same as first!
        ] ] }
        # boundary_json looks like { "type": "Polygon", "coordinates": [ [ [ 622982.347530439961702, 9761425.487526709213853 ], [ 622982.347530439961702, 9761456.744157770648599 ], [ 622946.255481739994138, 9761456.744157770648599 ], [ 622946.255481739994138, 9761441.115842230618 ], [ 622982.347530439961702, 9761425.487526709213853 ] ] ] }
        # return subpc.split("/")[-1], out["metadata"]["boundary_json"]
        return subpc.split("/")[-1], ret
    def _create_geojson(polygons):
        geojson = {"type": "FeatureCollection", "features": []}
        for (pcid, poly) in polygons:
            geojson["features"].append({"type": "Feature", "properties": { "id": pcid }, "geometry": poly })
        with shapefile.Writer("pointclouds/{}.shp".format(pointcloud.uid)) as w: # filename ignores extension and creates .shp, .dbf and .sh
            w.field("id", "C")
            w.field("Name", "C")
            for feature in filter(lambda f: len(f["geometry"]["coordinates"]) > 0, geojson["features"]): # only include features with an actual polygon
                w.record(feature["properties"]["id"], feature["properties"]["id"])
                w.shape(feature["geometry"])
    def _create_kml(orig_srs):
        return _call('ogr2ogr -a_srs "EPSG:4326" -s_srs "{1}" -t_srs "EPSG:4326" -f "KML" pointclouds/{0}.kml pointclouds/{0}.shp'.format(pointcloud.uid, orig_srs))

    print("Getting pointcloud bounds")
    
    srs = get_proj4_string(pointcloud)
    pointcloud.proj4 = srs
    print(repr(srs))
    if not srs:
        print("ERROR: PROJ4 string not set on original PC! Unable to compute object bounds!")
        return True
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for subpc in glob.glob("pointclouds/parts/{}/*.las".format(pointcloud.uid)):
            futures.append(executor.submit(_get_bound, subpc=subpc.replace("\\", "/")))
        # Wait for all futures to complete
        _create_geojson([future.result() for future in concurrent.futures.as_completed(futures)])
    ret = _create_kml(srs)
    print("Getting pointcloud bounds complete")
    return ret == 0
