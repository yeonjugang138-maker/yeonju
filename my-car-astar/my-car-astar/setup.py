import os
from glob import glob
from setuptools import setup

package_name = 'my_car_astar'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='yeonjugang',
    maintainer_email='yeonjugang138@gmail.com',
    description='A* + Pure Pursuit navigation with lidar avoidance and YOLOv8 emergency stop',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'astar_estop = my_car_astar.astar_estop:main',
        ],
    },
)
