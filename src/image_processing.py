from __future__ import annotations

__doc__ = """
    Process a single frame of the stream and get the timer value.
"""

import os
import re
from datetime import datetime
from math import isclose
from typing import Iterable, Optional

import cv2
import numpy as np
import pytesseract


class CroppedOcrError(Exception):
    pass

class TimeStringParsingError(Exception):
    pass



class LudFrame():
    TIME_REGEX = re.compile(r'(\d{1,2})[:\.]?(\d{2})[:\.]?(\d{2})')
    

    def __init__(self, arr: np.ndarray, record_ims=False, bbox=None):
        self.record_ims = record_ims
        self.img = arr
        self.bbox = bbox # [x, y, w, h]
        self.cropped = None
        self._write("image.png", arr)


        
    def _write(self, name, im):
        if self.record_ims:
            cv2.imwrite(os.path.join("demo_images", name), im)


    @classmethod
    def get_timestamp_from_str(cls, s: str) -> Optional[int]:
        cleaned = "".join(s.split()) # no whitespace

        res = cls.TIME_REGEX.findall(cleaned)
        if len(res) != 1:
            raise TimeStringParsingError(f"cleaned: {cleaned}")
        hour, minute, second = res[0]
        timestamp = 60 * 60 * int(hour) + 60 * int(minute) + int(second)
        return timestamp, ":".join(res[0])

    
    def get_str_from_cropped(self) -> str:
        """
        Convert a cropped image to a timestamp-convertible string.
        grayscale -> threshold -> filter out small shapes -> inversion -> tesseract OCR
        """
        if self.cropped is None:
            raise CroppedOcrError

        im_size = self.cropped.shape[0] * self.cropped.shape[1]
        min_area_thresh = (im_size)**0.5 / 5
        if min_area_thresh < 12:
            min_area_thresh = 4
        
        try:
            grayscale = cv2.cvtColor(self.cropped, cv2.COLOR_BGR2GRAY)
        except cv2.error:
            raise CroppedOcrError
        
        self._write('grayscale.png', grayscale)
        thresh = 80
        grayscale[grayscale <  thresh] = 0 # TODO
        grayscale[grayscale >= thresh] = 255
        black_white = grayscale
        self._write('black_white.png', black_white)
        
        
        # https://stackoverflow.com/questions/42798659/how-to-remove-small-connected-objects-using-opencv
        nb_components, output, stats, centroids = cv2.connectedComponentsWithStats(black_white, connectivity=8)
        sizes = stats[1:, -1]
        filtered = np.zeros(output.shape, np.uint8)
        #for every component in the image, you keep it only if it's above min_size
        for i, size in enumerate(sizes):
            if size >= min_area_thresh:
                filtered[output == i + 1] = 255
        self._write('filtered.png', filtered)

        inverted = cv2.bitwise_not(filtered)
        self._write('inverted.png', inverted)
        string = pytesseract.image_to_string(inverted, 'eng', config='-c tessedit_char_whitelist=0123456789:.')
        return string

    def update_bbox(
        self,
        color: Iterable[int] = [67, 12, 21], 
        color_threshold: int = 15,
        max_perimeter_tolerance: float = 0.20,
        min_area_factor: float = 0.01,
        morph_close_len: int = 3,
        border_width: int = 5
        ):

        """
        Get the timer portion of the frame.
        inRange mask -> Canny edge detection -> morphological dilate to complete path ->
        approximate rectangular contour with large area that fits well in its bounding box -> coordinates of bounding box
        """

        color = np.array(color) # BGR
        min_color, max_color = color - color_threshold, color + color_threshold
        mask = cv2.inRange(self.img, min_color, max_color)

        self._write('mask.png', mask)
        canny = cv2.Canny(mask, 127, 255)
        self._write('canny.png', canny)
        
        closed = cv2.dilate(canny, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_close_len,morph_close_len)))
        self._write('closed.png', closed)
        
        contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        approx_contours = [cv2.approxPolyDP(c, 0.1 * cv2.arcLength(c, True), True) for c in contours]

        best_bounding_box = [0, 0, 0, 0] # x, y, width, height
        best_peri_deviance = 1.0
        
        im_height, im_width, *_ = self.img.shape
        min_area = min_area_factor * im_height * im_width
        for cont in approx_contours:
            rect = cv2.boundingRect(cont)
            x, y, width, height = rect

            box_peri = cv2.arcLength(cont, True) 
            cont_peri = 2 * width + 2 * height

            area = width * height

            if area >= min_area \
            and isclose(cont_peri, box_peri, rel_tol=max_perimeter_tolerance) \
            and isclose(cont_peri, box_peri, rel_tol=best_peri_deviance) \
            and not isclose(width,  im_width,  rel_tol=0.1) \
            and not isclose(height, im_height, rel_tol=0.1):
                best_bounding_box = rect
                best_peri_deviance = abs(cont_peri - box_peri) / box_peri

        self.bbox = best_bounding_box
        self.crop()
        return self.bbox
        

    def crop(self, bounding_box=None):
        bbox = bounding_box if bounding_box else self.bbox
        x, y, w, h = bbox
        self.cropped = self.img[y:y+h, x:x+w]
    



if __name__ == '__main__':
    import pafy

    # (3, 6, 272, 157)
    #stream = pafy.new('https://www.youtube.com/watch?v=UzHtbjtT8hE').getbestvideo()
    #cap = cv2.VideoCapture(stream.url)
    #cap.set(1, 61320-1)
    #_, frame = cap.read()

    lf = LudFrame(cv2.imread('demo_images/image.png'), True)
    print(lf.update_bbox())
    print(lf.get_str_from_cropped())
    


