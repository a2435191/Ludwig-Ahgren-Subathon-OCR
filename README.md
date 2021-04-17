# Ludwig-Ahgren-Subathon-OCR

## Purpose
* Ludwig Ahgren, a popular streamer and YouTuber, livestreamed his entire life for around a month between March and April 2021.
* Every time a Twitch viewer donated, an onscreen timer would increase. If the timer ever decremented so far that it reached zero, the subathon would be over.
* This repo uses OpenCV and Tesseract OCR to scan the timer and record these timer values for anyone to use.
 
![29](https://user-images.githubusercontent.com/68962413/115126462-cb512100-9f94-11eb-8264-7c902472504a.png)

## Notes
* ~~This takes a while— even though the streaming and processing are done in separate threads, I only got around 2 frames analyzed per second.~~ Fixed with more threads! Now I can get ~9 hours of 360p footage (sampled 1/sec)  processed in only 90 minutes!
* See [data/csvs](data/csvs) and [data/images](data/images).

## TODO
* [x] Unscuff `video_timestamp` column
* [ ] Add proper `logging` support
* [ ] Make OCR more reliable— right now it is only 60-80%. This is my first project using OpenCV, so I'd appreciate any help.
* Specifically, the program fails when the timer flashes red or there is too much noise around the timer
* ~~[ ] In a similar vein, make 240p (or even 144p) usable.~~
* [x] More threads/processes— the program is usually *not* bound by network IO
* [ ] Write more tests
* [ ] Write proper docstrings
* [ ] Add SQL DB support
