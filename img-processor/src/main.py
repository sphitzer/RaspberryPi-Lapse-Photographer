import sys, os
import argparse
import cv2 as cv
import ffmpeg
import numpy as np
import math

def display_image():

    img = cv.imread(cv.samples.findFile("../test-images-jpeg/photo-20210210-093458.jpg"))

    if img is None:
        sys.exit("Could not read the image.")
    cv.imshow("Display window", img)
    k = cv.waitKey(0)
    if k == ord("s"):
        cv.imwrite("../test-images-jpeg/ohoto.png", img)

def edge_detection():
    # Loads an image
    src = cv.imread(cv.samples.findFile("../test-images-jpeg/photo-20210210-093458.jpg"), cv.IMREAD_GRAYSCALE)
    dst = cv.Canny(src, 100, 170, None, 3)
    
    # Copy edges to the images that will display the results in BGR
    cdst = cv.cvtColor(dst, cv.COLOR_GRAY2BGR)
    cdstP = np.copy(cdst)
    
    lines = cv.HoughLines(dst, 1, np.pi / 180, 150, None, 0, 0)
    
    if lines is not None:
        for i in range(0, len(lines)):
            rho = lines[i][0][0]
            theta = lines[i][0][1]
            a = math.cos(theta)
            b = math.sin(theta)
            x0 = a * rho
            y0 = b * rho
            pt1 = (int(x0 + 1000*(-b)), int(y0 + 1000*(a)))
            pt2 = (int(x0 - 1000*(-b)), int(y0 - 1000*(a)))
            cv.line(cdst, pt1, pt2, (0,0,255), 3, cv.LINE_AA)
    
    
    linesP = cv.HoughLinesP(dst, 1, np.pi / 180, 50, None, 50, 10)
    
    if linesP is not None:
        for i in range(0, len(linesP)):
            l = linesP[i][0]
            cv.line(cdstP, (l[0], l[1]), (l[2], l[3]), (0,0,255), 3, cv.LINE_AA)
    
    cv.imshow("Detected Lines (in red) - Standard Hough Line Transform", cdst)
    cv.waitKey()
    return 0

def generate_video():

    #create output folder in timelapse folder
    os.mkdir('../test-images-jpeg/output', 0o777)

    (
        ffmpeg
        .input('../test-images-jpeg/*.jpg', pattern_type='glob', framerate=60)
        .filter('deflicker', mode='pm', size=10)
        .filter('scale', size='3840x2160', force_original_aspect_ratio='increase')
        .output('../test-images-jpeg/output/movie.mp4', crf=20, preset='slow', movflags='faststart', pix_fmt='yuv420p')
        #.view(filename='filter_graph')
        .run()
    )

def livestream():
    (
        ffmpeg
        .input('FaceTime', format='avfoundation', pix_fmt='uyvy422', framerate=30)
        .output('out.mp4', pix_fmt='yuv420p', vframes=1000)
        .run()
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Timelapse via picamera or gphoto2')

    #parser.add_argument('--name', required=True, type=str, dest='name', help='name of folder timelapse to be saved in')
    #parser.add_argument('--outputpath', required=True, type=str, dest='output_path', help='output dir that will hold newly created timelapse dir')
    #parser.add_argument('--frames', required=True, type=int, dest='frames',
        #            help='total number of photos to be taken')
    #parser.add_argument('--interval', required=True, dest='interval', type=int,
        #            help='time between each photo in seconds')

    args = parser.parse_args()
    print(args)

    #display_image()
    #generate_video()
    #livestream()
    edge_detection()