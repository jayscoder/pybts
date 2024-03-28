# 发布到pypi上
python setup.py sdist bdist_wheel
twine upload dist/*
twine upload --repository-url https://test.pypi.org/legacy/ dist/* # 测试上传
