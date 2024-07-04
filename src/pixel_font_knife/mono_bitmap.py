from collections import UserList


class MonoBitmap(UserList[list[int]]):
    @staticmethod
    def cost(source: list[list[int]]) -> 'MonoBitmap':
        bitmap = MonoBitmap(0, 0)
        bitmap.width = len(source[0])
        bitmap.height = len(source)
        for source_row in source:
            if bitmap.width != len(source_row):
                raise ValueError('Rows widths unequal')
            bitmap.append([0 if alpha == 0 else 1 for alpha in source_row])
        return bitmap

    width: int
    height: int

    def __init__(self, width: int, height: int, alpha: int = 0):
        super().__init__()
        self.width = width
        self.height = height
        for _ in range(height):
            self.append([alpha] * width)
