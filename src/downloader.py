import os
import time
import concurrent.futures as cf
from queue import Queue
from threading import Thread, Lock

import cv2
import pafy
import pandas
from math import ceil

from image_processing import CroppedOcrError, LudFrame, TimeStringParsingError


class LudVideo():
    
    def __init__(self, url, dest, record_ims=False):
        self.record_ims = record_ims
        self.dest = dest
        self.url = url
        self._q = Queue(100)
        self.get_frames_done = False


        self.video = pafy.new(self.url)
        self.length = self.video.length

        for v in self.video.videostreams:
            if v.dimensions[1] == 360:
                self.stream = v
                break

        
        self.sample_capture = cv2.VideoCapture(self.stream.url)
        self.fps = self.sample_capture.get(cv2.CAP_PROP_FPS)
        self.frames = self.fps * self.length

        self.df = pandas.read_csv(self.dest, index_col=['vid_url', 'frame'])

        self.df_lock = Lock()

        

    def get_frames(self, start_frame, end_frame):
        frames_num = 0
        total_frames_count = start_frame

        capture = cv2.VideoCapture(self.stream.url)
        capture.set(1, start_frame)

        while total_frames_count < end_frame:
            check = capture.grab()

            if not check:
                print(f'from {start_frame} to {end_frame} is breaking')
                break
                
            if frames_num == 0:
                _, frame = capture.retrieve()
                self._q.put((total_frames_count, frame))


            frames_num = (frames_num + 1) % self.fps
            total_frames_count += 1
        print(f'from {start_frame} to {end_frame} is completed')
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
            self.df.loc[(self.url, idx), :] = [f"{hour:03}:{minutes:02}:{seconds:02}", ts, string]
            self.df.to_csv(self.dest)

 


    def go(self, download_workers=3, processing_workers=2, start_frac=0, end_frac=1):
        # https://stackoverflow.com/questions/41648103/how-would-i-go-about-using-concurrent-futures-and-queues-for-a-real-time-scenari
        with cf.ThreadPoolExecutor(max_workers=download_workers+processing_workers) as executor: 
            
            counter = start_frac * self.frames
            get_frames_per_fut = ceil(self.frames / download_workers)
            futs = [
                executor.submit(
                    self.get_frames, 
                    int( (i+start_frac) * get_frames_per_fut ), 
                    int( (i+end_frac)   * get_frames_per_fut )
                ) for i in range(download_workers)
            ]
            while futs:
                done, _ = cf.wait(futs, timeout=0.5, return_when=cf.FIRST_COMPLETED)
                while not self._q.empty() and len(futs) < download_workers + processing_workers:       
                    idx, frame = self._q.get(True)
                    futs.append(executor.submit(self.process_frame, idx, frame))
                for future in done:
                    futs.remove(future)
                    counter += self.fps
                os.system('clear')
                print(
                    f"{counter/(end_frac*self.frames)} done, \
                    len(futs) == {len(futs)}, \
                    self._q.qsize() == {self._q.qsize()}"
                )
        print('done')
                

if __name__ == '__main__':
    lv = LudVideo('https://www.youtube.com/watch?v=UzHtbjtT8hE', 'test_data.csv')
    lv.go(3, 7, 0.28)
    
