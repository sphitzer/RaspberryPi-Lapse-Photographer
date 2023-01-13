#imports needed for these functions
#import cv2 as cv
#import numpy as np
#import math
#import openai
#import ffmpeg


def livestream():
    (
        ffmpeg
        .input('FaceTime', format='avfoundation', pix_fmt='uyvy422', framerate=5)
        .output('out.mp4', pix_fmt='yuv420p', vframes=1000)
        .run()
    )

def openai_test():
    #import key from .env
    return None
    

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


