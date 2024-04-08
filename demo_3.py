import stable_baselines3

class A:
    def __init__(self):
        self.x = 1

class B:
    def __init__(self):
        self.y = 1


class C(A, B):
    pass

c = C()

print(c.x, c.y)

if __name__ == '__main__':
    pass
