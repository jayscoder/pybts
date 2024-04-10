import stable_baselines3
from pybts import Builder

if __name__ == '__main__':
    builder = Builder(folders=['logs', 'demos'])
    print(builder.get_relative_filename('demos/demos/demo_1.xml'))
