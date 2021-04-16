import concurrent.futures as cf
import os
import sys
import time
from math import ceil, isclose
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
            if v.dimensions[1] == 360 and v.extension == 'mp4':
                self.stream = v
                break

        
        self.sample_capture = cv2.VideoCapture(self.stream.url)

        self.total_frames = int(self.sample_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frames = int(self.total_frames * (crop_right - crop_left))
        self.frames_offset = self.total_frames * crop_left
        self.fps = self.sample_capture.get(cv2.CAP_PROP_FPS)
        self.ms_per_frame = 1000 / self.fps
        
    
        self.df = pandas.read_csv(self.dest, index_col=['frame'])

        self.df_lock = Lock()

        

    def get_frames(self, start_frame, end_frame):
        frames_completed = 0

        capture = cv2.VideoCapture(self.stream.url)
        capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        old_ms = capture.get(cv2.CAP_PROP_POS_MSEC)

        while frames_completed < end_frame - start_frame:
            check = capture.grab()

            
            if not check:
                break
             
            
            if (ms := capture.get(cv2.CAP_PROP_POS_MSEC)) // 1000 != old_ms // 1000: # no more than one queue put every second
                old_ms = ms
                if abs(ms % 1000 - 1000) < self.ms_per_frame or abs(ms % 1000) < self.ms_per_frame:
                    _, frame = capture.retrieve()
                    self._q.put((int(ms / 1000 * self.fps), frame))

            frames_completed += 1

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

        with self.lines_completed_lock:
            self.lines_completed += 1
            

 


    def go(self, download_workers=3, processing_workers=2, start_frac=0):

        # https://stackoverflow.com/questions/41648103/how-would-i-go-about-using-concurrent-futures-and-queues-for-a-real-time-scenari
        with cf.ThreadPoolExecutor(max_workers=download_workers+processing_workers) as executor: 
            self.lines_completed = self.frames * start_frac / self.fps
            self.lines_completed_lock = Lock()

            start_time = time.time()
            
            get_frames_per_fut = ceil(self.frames * (1 - start_frac) / download_workers)

            futs = [
                executor.submit(
                    self.get_frames, 
                    int( (i+start_frac) * get_frames_per_fut + self.frames_offset),
                    int( (i+1         ) * get_frames_per_fut + self.frames_offset)
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
                        
                    
                    with self.lines_completed_lock:
                        frac_done = self.lines_completed / (self.frames / self.fps)

                    elapsed = time.time() - start_time
                    if frac_done != start_frac:
                        time_remaining = round( (1 - frac_done - start_frac) * elapsed / (frac_done - start_frac) / 3600, 5 )
                    else:
                        time_remaining = None

                    os.system('clear')
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
    lv = LudVideo('https://www.youtube.com/watch?v=pRygmplZV6M', 'test_data2.csv', 0.999, 1)
    lv.go(1, 10)

