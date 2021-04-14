# Ludwig-Ahgren-Subathon-OCR

## Purpose
* Ludwig Ahgren, a popular streamer and YouTuber, livestreamed his entire life for around a month between March and April 2021.
* Every time a Twitch viewer donated, an onscreen timer would increase. If the timer ever decremented so far that it reached zero, the subathon would be over.
* This repo uses OpenCV and Tesseract OCR to scan the timer and record these timer values for anyone to use.

## Notes
* This takes a while— even though the streaming and processing are done in separate threads, I only got around 2 frames analyzed per second.
* For this reason, only a sample `.csv` file is included in the project. The source is [this vod](https://www.youtube.com/watch?v=UzHtbjtT8hE).
* Pull requests from people with good Internet are always appreciated!
