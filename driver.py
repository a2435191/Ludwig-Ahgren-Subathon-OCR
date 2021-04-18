from src.downloader import LudVideo

lv = LudVideo('https://www.youtube.com/watch?v=eWkyGGpl6GA', 'data/csvs/raw/27.csv', 480)
lv.go(2, 25)