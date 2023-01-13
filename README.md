# RaspberryPi-Lapse-Photographer
Fast API projects to capture, process, ffmpeg & upload the timelapse photos


# Top TODO
* replace argparse with proper orchestration....but what?
* standardize on loguru in both scripts

## photographer
Code to capture the photographs & control timelapse functionality

### install global dependencies for photographer
https://github.com/jim-easterbrook/python-gphoto2#install-with-pip

install libgphoto2
```brew install libgphoto2```
install gphoto2
```sudo pip3 install -v gphoto2 --no-binary :all:```

gphoto2 examples: https://github.com/jim-easterbrook/python-gphoto2/tree/master/examples

### create a timelapse
* exmaple execution w/ argparse: `python3 ./src/main.py --name e2e-test  --outputpath ../test-timelapses --frames 5 --interval 5`

* example exeuction via docker: `docker run -t -i --privileged -v /dev/bus/usb:/dev/bus/usb <image>`

## img-processor
Code to edit photos & generate timelapse 

* example execution w/ argparse `python3 ./src/main.py --name squid --timelapsedir ../test-timelapses/e2e-test-2 --s3bucket <s3bucket>`

  ### todo
  * add method to strip metadata
  * openai touches...?
  

### prereqs
* opencv setup for m1 mac: https://blog.roboflow.com/m1-opencv/
* install ffmpeg and have available via path: ```brew install ffmpeg```


### Other todo
* look into using unity as part of this workflow??
* but how to edit the photos?  
  * opencv ?  other options here...?
  * what are we doing with the photos?
       * basics like crop, quality adjustmnet
           * what else?
       * make an adjustment to the image on a frame by frame basis for a good effect
  * use a 'module' style system for open cv edits so that at timelapse generation time they can be adjusted/combined

