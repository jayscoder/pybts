import stable_baselines3


class A:
    def __init__(self):
        self.x = 1


class B:
    def __init__(self):
        self.y = 1


class C(A, B):
    z = 10

    def __init__(self):
        A.__init__(self)
        B.__init__(self)


c = C()

print(c.x, c.y, c.z)
print(c.__dict__)
print(C.__dict__)
from collections import defaultdict

if __name__ == '__main__':
    d = defaultdict(int)
    d['a'] = defaultdict(int)
    d['a']['b'] = 1
    import json

    print(json.dumps(d))
