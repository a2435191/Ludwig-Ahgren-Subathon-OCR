import os
import time
from queue import Queue
from threading import Thread

import cv2
import pafy
import pandas

from image_processing import CroppedOcrError, LudFrame, TimeStringParsingError


class LudVideo():
    def __init__(self, url, dest, start_at_frame=0, record_ims=False):
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

        self.capture = cv2.VideoCapture(self.stream.url)
        self.prev_frame = start_at_frame
        if self.prev_frame > 30:
            self.capture.set(1, (self.prev_frame//30 * 30 + 29))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)

        self.df = pandas.read_csv(self.dest, index_col=['vid_url', 'frame'])
        self.last_frame = None

        

        

    def get_frames(self):
        frames_count = 0
        total_frames_done = self.prev_frame
        while True:
            check = self.capture.grab()

            if not check:
                self.get_frames_done = True
                break
                

            if frames_count == 0:
                _, frame = self.capture.retrieve()
                self._q.put((total_frames_done, frame))


            frames_count = (frames_count + 1) % self.fps
            total_frames_done += 1
            

        self.capture.release()
        print('done with get_frames')


    def recalculate_bbox(self, frame=None):
        if frame is None:
            frame = self.last_frame
        if frame is None:
            return
        frame.update_bbox()
        frame.crop()


    def ocr_frame(self, recurse=False):
        try:
            formatted_string = self.last_frame.get_str_from_cropped()
        except CroppedOcrError:
            if recurse:
                return ""
            self.last_frame.update_bbox()
            formatted_string = self.ocr_frame(True)
                
        return formatted_string

    def format_from_str(self, string, recurse=False):
        try:
            ts, string = LudFrame.get_timestamp_from_str(string)
        except TimeStringParsingError:
            if recurse:
                return -1, ""
            self.last_frame.update_bbox()
            ts, string = self.format_from_str(self.ocr_frame(True), True)

        return ts, string

        

    def process_frames(self):
        while True:
            if self.get_frames_done and self._q.empty():
                break
            idx, frame = self._q.get(True)
            print(self._q.qsize())
            self.last_frame = LudFrame(frame, self.record_ims)

            raw_ocr_string = self.ocr_frame()
            ts, string = self.format_from_str(raw_ocr_string)

            raw_seconds = idx / self.fps
            hour = int(raw_seconds // 3600)
            seconds = int(raw_seconds % 60)
            minutes = int((raw_seconds // 60) % 60)

            self.df.loc[(self.url, idx), :] = [f"{hour:03}:{minutes:02}:{seconds:02}", ts, string]
            self.df.to_csv(self.dest)

            os.system('clear')
            print((idx // self.fps / self.length) * 100, "pct. complete")
        print('done with process_frames')
            


    def go(self):
        self.p_thread = Thread(target=self.process_frames, daemon=True)
        self.p_thread.start()

        self.g_thread = Thread(target=self.get_frames, daemon=True)
        self.g_thread.start()

        self.p_thread.join()
        self.g_thread.join()
        print('done with program')


if __name__ == '__main__':
    lv = LudVideo('https://www.youtube.com/watch?v=UzHtbjtT8hE', 'test_data.csv', record_ims=True)
    lv.go()
    
