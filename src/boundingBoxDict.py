
class BoundingBoxDict(dict):
    """
    For multithreaded to be efficient, we need to store the bounding boxes
    in a dictionary (as opposed to as an instance variable). However, instead
    of recomputing each bounding box for each frame key, we use the nearest box
    whose frame id is less.
    
    ...but each call to update_bbox takes < 5 ms, so
    I'll leave it be. This file stays for future updates in which
    update_bbox may be more costly.
    """
    def __getitem__(self, key):
        if not self:
            return

        if (val := super().get(key)) is not None:
            return val
        
        last_key = None
        for k in sorted(self.keys()):
            if k > key:
                try:
                    return super().__getitem__(last_key)
                except KeyError:
                    return
            last_key = k
        return super().__getitem__(last_key)

if __name__ == '__main__':
    bbd = BoundingBoxDict()
    bbd.update({1: ["a"], 5: ["b"], 6: ["c"], 18: ['d']})
    print(bbd[6])
