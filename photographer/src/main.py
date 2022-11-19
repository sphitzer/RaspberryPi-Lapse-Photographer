import gphoto2 as gp
import os, sys, time
import subprocess
import argparse
import logging
from loguru import logger
import fastapi
import random
gp.error_severity[gp.GP_ERROR] = logging.DEBUG

# create the directory that will house photos captured by the timelapse 
def create_timelapse_dir(output_path, tl_name):
    try:
        original_umask = os.umask(0)
        os.mkdir(output_path + '/' + tl_name, 0o777)
        os.mkdir(output_path + '/' + tl_name + '/capture', 0o777)
        
    except OSError as ose:
        if not os.listdir(output_path + '/' + tl_name + '/capture'):
            print('Directory with name %s exists, but capture directory is empty.  Creating timelapse...' % tl_name)
        else: 
            print('Timelapse with the name %s already exists' % tl_name)
            sys.exit(1)
    else:
        print('Creating timelapse... Photos located under /%s/capture ' % tl_name)
    finally:
        os.umask(original_umask)

    return 

# create camera instance, detect connected cameras via usb
def connect_camera():
    camera = gp.Camera()

    while True:
        try:
            camera.init()
        except gp.GPhoto2Error as ex:
            if ex.code == gp.GP_ERROR_MODEL_NOT_FOUND:
                print("No camera connected - checking again in 10 seconds")
                print("EX CODE: " + str(ex.code))
                # no camera, try again in 10 seconds
                time.sleep(10)
                continue
            # some other error we can't handle here
            raise

        # on connection, print camera information & exit loop
        # re-add this as debug logging
        #print('Summary')
        #print('=======')
        #print(camera.get_summary())
        break
    
    return camera


#WIP, untested...
def execute_timelapse(camera, capture_path, interval, frames):

    for x in range(frames):
        file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
        print('Camera file path: {0}/{1}'.format(file_path.folder, file_path.name))
        target = os.path.join(capture_path, file_path.name)
        print('Copying image to', target)
        camera_file = camera.file_get(
        file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
        camera_file.save(target)
        time.sleep(interval)
        #subprocess.call(['xdg-open', target])


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Timelapse via picamera or gphoto2')

    parser.add_argument('--name', required=True, type=str, dest='name', help='name of folder timelapse to be saved in')
    parser.add_argument('--outputpath', required=True, type=str, dest='output_path', help='output dir that will hold newly created timelapse dir')
    parser.add_argument('--frames', required=True, type=int, dest='frames',
                    help='total number of photos to be taken')
    parser.add_argument('--interval', required=True, dest='interval', type=int,
                    help='time between each photo in seconds')

    args = parser.parse_args()
    print(args)

    #create directory
    capture_path = os.path.join(args.output_path, args.name, 'capture')
    print(capture_path)
    create_timelapse_dir(args.output_path, args.name)

    #create camera instance
    camera = connect_camera()

    #run timelapse sequence
    execute_timelapse(camera, capture_path, args.interval, args.frames)

    #exit camera instance
    camera.exit()

