import os, sys
currentdir = os.path.join(os.path.dirname(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(os.path.join(parentdir, 'src'))

import unittest
from unittest import TestCase
from image_processing import LudFrame
import cv2

class ImageProcessingTest(TestCase):

    def test_all(self):
        for s in os.listdir('tests/test_images'):
            time, _ = os.path.splitext(s)
            hours, minutes, seconds = time.split(':')
            test_ts = 3600 * int(hours) + 60 * int(minutes) + int(seconds)
            
            with self.subTest(f"Image {s}"):
                lf = LudFrame(cv2.imread(f'tests/test_images/{s}'), True)
                lf.update_bbox()
                ts, _ = lf.get_timestamp_from_str(lf.get_str_from_cropped())
                self.assertEqual(test_ts, ts, f"Image {s} failed!")

if __name__ == '__main__':
    unittest.main() 
