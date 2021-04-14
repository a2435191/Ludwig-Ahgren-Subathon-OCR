import os
import time
from queue import Queue
from threading import Thread

import cv2
import pafy
import pandas

from image_processing import CroppedOcrError, LudFrame, TimeStringParsingError


class LudVideo():
    def __init__(self, url, prev_frame=0):
        self.url = url
        self._q = Queue()
        self.get_frames_done = False


        self.video = pafy.new(self.url)
        self.length = self.video.length
        for v in self.video.videostreams:
            if v.dimensions[1] == 360:
                self.stream = v
                break

        self.capture = cv2.VideoCapture(self.stream.url)
        self.prev_frame = prev_frame
        if self.prev_frame > 30:
            self.capture.set(1, (self.prev_frame//30 * 30 + 29))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)

        self.x, self.y, self.w, self.h = [0, 0, 0, 0] # x, y, w, h for crop box
        self.csv = pandas.read_csv('data.csv', index_col=['vid_url', 'frame'])
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

    def crop(self, frame):
        return frame[self.y:self.y+self.h, self.x:self.x+self.w]

    def recalculate_bbox(self, frame=None):
        if frame is None:
            frame = self.last_frame
        if frame is None:
            return
        self.x, self.y, self.w, self.h = LudFrame(frame).get_cropped()


    def ocr_frame(self, frame, recurse=False):
        cropped = self.crop(frame)
        try:
            formatted_string = LudFrame.get_str_from_cropped(cropped)
        except CroppedOcrError:
            if recurse:
                return ""
            self.recalculate_bbox()
            formatted_string = self.ocr_frame(frame, True)
                
        return formatted_string

    def format_from_str(self, string, recurse=False):
        try:
            ts, string = LudFrame.get_timestamp_from_str(string)
        except TimeStringParsingError:
            if recurse:
                return -1, ""
            self.recalculate_bbox()
            ts, string = self.format_from_str(self.ocr_frame(self.last_frame, True), True)

        return ts, string

        

    def process_frames(self):
        while True:
            if self.get_frames_done and self._q.empty():
                break
            idx, self.last_frame = self._q.get(True)

            cv2.imwrite("image.png", self.last_frame)

            raw_ocr_string = self.ocr_frame(self.last_frame)
            ts, string = self.format_from_str(raw_ocr_string)

            raw_seconds = idx / self.fps
            hour = raw_seconds // 3600
            seconds = raw_seconds % 60
            minutes = raw_seconds // 60

            self.csv.loc[(self.url, idx), :] = [f"{hour}:{minutes}:{seconds}", ts, string]
            self.csv.to_csv('data.csv')

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
    lv = LudVideo('https://www.youtube.com/watch?v=UzHtbjtT8hE', 991650)
    lv.go()
    
