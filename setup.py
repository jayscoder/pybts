from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
        name="pybt",
        version='1.0.0',
        description="pybt is a Python library for creating, managing, and visualizing behavior trees. It supports loading and exporting behavior trees from JSON and XML files, enables real-time visualization of execution processes, and allows for analysis of historical data",
        long_description=long_description,
        long_description_content_type='text/markdown',
        url='https://github.com/wangtong2015/pybt',
        author="Wang Tong",
        author_email="astroboythu@gmail.com",
        license="MIT",
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Topic :: Games/Entertainment :: Simulation',
            'Intended Audience :: Developers',
            'Intended Audience :: End Users/Desktop',
            'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3 :: Only'
        ],
        keywords='Behavior Tree Reinforcement Learning',
        install_requires=['jinja2'],
        packages=find_packages(),
        include_package_data=True,  # 指示包含在包中的数据文件
        python_requires='>=3.6',
        entry_points={
            'console_scripts': [
                'pybt=pybt.board_server:main',  # 确认这里是正确的路径到您的Flask app启动函数
            ],
        },
)
