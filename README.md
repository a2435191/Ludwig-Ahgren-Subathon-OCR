# Ludwig-Ahgren-Subathon-OCR

## Purpose
* Ludwig Ahgren, a popular streamer and YouTuber, livestreamed his entire life for around a month between March and April 2021.
* Every time a Twitch viewer donated, an onscreen timer would increase. If the timer ever decremented so far that it reached zero, the subathon would be over.
* This repo uses OpenCV and Tesseract OCR to scan the timer and record these timer values for anyone to use.

## Notes
* This takes a while— even though the streaming and processing are done in separate threads, I only got around 2 frames analyzed per second.
* For this reason, only a [sample `.csv` file](data.csv) is included in the project. The source is [this vod](https://www.youtube.com/watch?v=UzHtbjtT8hE).
* Pull requests from people with good Internet are always appreciated!

## TODO
* Unscuff `video_timestamp` column
* Add propper `logging` support
* Make OCR more reliable— right now it is only 82.4%. This is my first project using OpenCV, so I'd appreciate any help.
* In a similar vein, make 240p (or even 144p) usable.
* Use literally any other file format than csv
* More threads/processes— the program is usually *not* bound by network IO
* Write more tests
* Add readme/wiki detailing image processing algorithms
