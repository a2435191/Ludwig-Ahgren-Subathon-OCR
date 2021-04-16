import concurrent.futures as cf
import os
import sys
import time
from math import ceil
from queue import Queue
from threading import Lock, Thread

import cv2
import pafy
import pandas

from image_processing import CroppedOcrError, LudFrame, TimeStringParsingError


class LudVideo():
    
    def __init__(self, url, dest, crop_left=0, crop_right=1, record_ims=False):
        assert crop_left < crop_right
        self.crop_left  = crop_left
        self.crop_right = crop_right
        self.record_ims = record_ims
        self.dest = dest
        self.url = url
        self._q = Queue(1000)
        self.get_frames_done = False


        self.video = pafy.new(self.url)
        self.length = self.video.length * (crop_right - crop_left)
        

        for v in self.video.videostreams:
            if v.dimensions[1] == 360:
                self.stream = v
                break

        
        self.sample_capture = cv2.VideoCapture(self.stream.url)
        self.fps = self.sample_capture.get(cv2.CAP_PROP_FPS)
        self.frames = self.fps * self.length

        self.df = pandas.read_csv(self.dest, index_col=['frame'])

        self.df_lock = Lock()

        

    def get_frames(self, start_frame, end_frame):
        frames_num = 0
        total_frames_count = int(start_frame)

        capture = cv2.VideoCapture(self.stream.url)
        capture.set(1, start_frame)

        while total_frames_count < end_frame:
            check = capture.grab()

            if not check:
                break
                
            if frames_num == 0:
                _, frame = capture.retrieve()
                self._q.put((total_frames_count, frame))


            frames_num = int( (frames_num + 1) % self.fps )
            total_frames_count = int(total_frames_count + 1)

        capture.release()


    def ocr_frame(self, frame):
        for _ in range(2):
            try:
                formatted_string = frame.get_str_from_cropped()
                return formatted_string
            except CroppedOcrError:
                frame.update_bbox()
 
        return ""

    def format_from_str(self, frame, string, recurse=False):
        for _ in range(2):
            try:
                ts, string = LudFrame.get_timestamp_from_str(string)
                return ts, string
            except TimeStringParsingError:
                frame.update_bbox()

        return -1, ""

        

    def process_frame(self, idx, frame):
        frame = LudFrame(frame, self.record_ims)

        raw_ocr_string = self.ocr_frame(frame)
        ts, string = self.format_from_str(frame, raw_ocr_string)

        raw_seconds = idx / self.fps
        hour = int(raw_seconds // 3600)
        seconds = int(raw_seconds % 60)
        minutes = int((raw_seconds // 60) % 60)

        with self.df_lock:
            self.df.loc[idx, :] = [f"{hour:03}:{minutes:02}:{seconds:02}", ts, string]
            self.df.to_csv(self.dest)
            

 


    def go(self, download_workers=3, processing_workers=2, start_frac=0, end_frac=1):

        # https://stackoverflow.com/questions/41648103/how-would-i-go-about-using-concurrent-futures-and-queues-for-a-real-time-scenari
        with cf.ThreadPoolExecutor(max_workers=download_workers+processing_workers) as executor: 
            start_time = time.time()
            counter = start_frac * self.frames
            get_frames_per_fut = ceil(self.frames * (end_frac - start_frac)/ download_workers)

            futs = [
                executor.submit(
                    self.get_frames, 
                    int( (i+start_frac) * get_frames_per_fut + self.crop_left) // 30 * 30, 
                    int( (i+end_frac)   * get_frames_per_fut + self.crop_left) // 30 * 30
                ) for i in range(download_workers)
            ]
            while futs:
                try:
                    done, _ = cf.wait(futs, timeout=1, return_when=cf.FIRST_COMPLETED)
                    while not self._q.empty() and len(futs) < download_workers + processing_workers:       
                        idx, frame = self._q.get(True)
                        futs.append(executor.submit(self.process_frame, idx, frame))
                    for future in done:
                        futs.remove(future)
                        counter += self.fps
                    os.system('clear')
                    frac_done = counter/(end_frac*self.frames)

                    elapsed = time.time() - start_time
                    if frac_done != start_frac:
                        time_remaining = round( (1 - frac_done - start_frac) * elapsed / (frac_done - start_frac) / 3600, 5 )
                    else:
                        time_remaining = None
                    print(
                        f"frac_done == {frac_done},\
                        len(futs) == {len(futs)},\
                        self._q.qsize() == {self._q.qsize()},\
                        time_remaining == {time_remaining} hours"
                    )
                except KeyboardInterrupt:
                    break
        print('done')
                

if __name__ == '__main__':
    lv = LudVideo('https://www.youtube.com/watch?v=pRygmplZV6M', 'test_data.csv')
    lv.go(2, 50)

