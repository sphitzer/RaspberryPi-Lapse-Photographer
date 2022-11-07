# Top TODO
* implement basics like argparse interface & logging in both

# RaspberryPi-Lapse-Photographer
Fast API projects to capture, process, ffmpeg & upload the timelapse photos

https://github.com/jim-easterbrook/python-gphoto2#install-with-pip

## photographer
Code to capture the photographs & control timelapse functionality

### install global dependencies for photographer
install libgphoto2
```brew install libgphoto2```
install gphoto2
```sudo pip3 install -v gphoto2 --no-binary :all:```

Examples: https://github.com/jim-easterbrook/python-gphoto2/tree/master/examples


## img-processor
Code to edit photos & generate timelapse 

### prereqs
* opencv setup for m1 mac: https://blog.roboflow.com/m1-opencv/
* install ffmpeg and have available via path: ```brew install ffmpeg```


* look into using unity as part of this workflow??
* but how to edit the photos?  
  * opencv ?  other options here...?
  * what are we doing with the photos?
       * basics like crop, quality adjustmnet
           * what else?
       * make an adjustment to the image on a frame by frame basis for a good effect
            * could use opencv to identify 
  * use a 'module' style system for open cv edits so that at timelapse generation time they can be adjusted/combined

