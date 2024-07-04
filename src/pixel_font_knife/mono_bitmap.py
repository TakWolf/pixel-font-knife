from collections import UserList


class MonoBitmap(UserList[list[int]]):
    width: int
    height: int

    def __init__(self, width: int, height: int, alpha: int = 0):
        super().__init__()
        self.width = width
        self.height = height
        for _ in range(height):
            self.append([alpha] * width)
